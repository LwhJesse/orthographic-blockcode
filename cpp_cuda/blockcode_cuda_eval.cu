/*
  blockcode_cuda_eval.cu

  CUDA/C++ prototype evaluator for the Orthographic BlockCode project.

  Purpose
  -------
  This is a correctness-first GPU backend prototype.

  It evaluates a batch of mappings J against a fixed article/corpus x.

  CPU responsibilities:
    - Parse dirty article.
    - Parse lexicon and rules.
    - Add literal fallback rules.
    - Enumerate segmentation templates for each lexicon word.
    - Convert article into (word_id, delimiter_type) counts.
    - Generate/parse mapping batch.

  GPU responsibilities:
    - For each mapping J, word, and delimiter type:
        path -> packed code
        code -> candidate rank by brute-force code collision search
        word+delimiter -> minimum cost
    - Reduce article cost for each mapping.

  Important
  ---------
  This is NOT the final high-performance CUDA design.
  Candidate ranking is intentionally brute-force:
    for target code, scan all words and their paths to determine rank.
  That is slow but simple and exact enough for small research tests.

  Later versions should replace this with sort/reduce over emitted
  (mapping_id, packed_code, word_id) entries using CUB/Thrust.

  Build
  -----
    cmake -S cpp_cuda -B build-cuda -DCMAKE_BUILD_TYPE=Release
    cmake --build build-cuda -j

  Run
  ---
    ./build-cuda/blockcode_cuda_eval \
      --rules configs/rules_v1.tsv \
      --lexicon data/examples/mini_lexicon.tsv \
      --article data/examples/sample_article.txt \
      --out out/cuda_sample

  Optional mapping batch
  ----------------------
    --mappings mappings.tsv

  mappings.tsv format:
    mapping_id<TAB>rule_id<TAB>code

  If omitted, one default mapping is evaluated using the `code` column
  in rules_v1.tsv.
*/

#include <cuda_runtime.h>

#include <algorithm>
#include <cassert>
#include <cctype>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <functional>
#include <iostream>
#include <limits>
#include <map>
#include <regex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

#define CUDA_CHECK(call) do {                                           \
  cudaError_t err__ = (call);                                            \
  if (err__ != cudaSuccess) {                                            \
    std::cerr << "CUDA error at " << __FILE__ << ":" << __LINE__       \
              << ": " << cudaGetErrorString(err__) << std::endl;        \
    std::exit(1);                                                        \
  }                                                                      \
} while (0)

enum Scope : int {
  SCOPE_ANY = 0,
  SCOPE_PREFIX = 1,
  SCOPE_SUFFIX = 2,
  SCOPE_WHOLE = 3
};

enum Delim : int {
  D_EOF = 0,
  D_SPACE = 1,
  D_NEWLINE = 2,
  D_COMMA = 3,
  D_COMMA_SPACE = 4,
  D_PERIOD = 5,
  D_PERIOD_SPACE = 6,
  D_SEMI = 7,
  D_SEMI_SPACE = 8,
  D_COLON = 9,
  D_COLON_SPACE = 10,
  D_QMARK = 11,
  D_QMARK_SPACE = 12,
  D_EXCL = 13,
  D_EXCL_SPACE = 14,
  D_OTHER = 15,
  D_COUNT = 16
};

struct Settings {
  int raw_prefix_cost = 1;
  int max_encoded_word_len = 48;
  int max_paths_per_word = 512;
  int max_candidate_rank = 3;
};

struct Rule {
  std::string rule_id;
  std::string chunk;
  char code = 0;       // one-key code, a-z
  Scope scope = SCOPE_ANY;
  bool enabled = true;
  bool literal = false;
};

struct Word {
  std::string text;
  int freq = 1;
};

struct PathTmp {
  int word_id = -1;
  std::vector<int> rule_ids;
};

struct HostData {
  std::vector<Rule> rules;
  std::vector<Word> words;
  std::unordered_map<std::string, int> word_to_id;

  std::vector<PathTmp> paths;
  std::vector<int> word_path_begin;
  std::vector<int> word_path_end;

  std::vector<int> flat_path_rules;
  std::vector<int> path_offsets;
  std::vector<int> path_word;

  std::vector<int> article_counts; // [word_count * D_COUNT]
  int literal_base_cost = 0;
  int baseline_total = 0;
  int uppercase_extra_total = 0;
};

static std::string trim_ascii(const std::string& s) {
  size_t b = 0;
  size_t e = s.size();
  while (b < e && std::isspace(static_cast<unsigned char>(s[b]))) ++b;
  while (e > b && std::isspace(static_cast<unsigned char>(s[e - 1]))) --e;
  return s.substr(b, e - b);
}

static std::vector<std::string> split_tab(const std::string& line) {
  std::vector<std::string> out;
  std::string cur;
  std::stringstream ss(line);
  while (std::getline(ss, cur, '\t')) out.push_back(trim_ascii(cur));
  return out;
}

static std::string lower_ascii(std::string s) {
  for (char& c : s) c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
  return s;
}


static bool is_ascii_alpha_string(const std::string& s) {
  if (s.empty()) return false;
  for (unsigned char c : s) {
    if (!std::isalpha(c) || c >= 128) return false;
  }
  return true;
}

static Scope parse_scope(const std::string& s) {
  if (s == "any") return SCOPE_ANY;
  if (s == "prefix") return SCOPE_PREFIX;
  if (s == "suffix") return SCOPE_SUFFIX;
  if (s == "whole") return SCOPE_WHOLE;
  throw std::runtime_error("unknown scope: " + s);
}

static std::vector<Rule> load_rules_tsv(const std::string& path) {
  std::ifstream f(path);
  if (!f) throw std::runtime_error("cannot open rules: " + path);

  std::string header;
  std::getline(f, header);
  auto cols = split_tab(header);
  std::unordered_map<std::string, int> idx;
  for (int i = 0; i < (int)cols.size(); ++i) idx[cols[i]] = i;

  auto get = [&](const std::vector<std::string>& parts, const std::string& name) -> std::string {
    auto it = idx.find(name);
    if (it == idx.end() || it->second >= (int)parts.size()) return "";
    return parts[it->second];
  };

  std::vector<Rule> rules;
  std::string line;
  while (std::getline(f, line)) {
    if (line.empty()) continue;
    auto p = split_tab(line);
    std::string enabled = get(p, "enabled");
    if (!(enabled == "1" || enabled == "true" || enabled == "TRUE")) continue;

    Rule r;
    r.rule_id = get(p, "rule_id");
    r.chunk = lower_ascii(get(p, "chunk"));
    std::string code = lower_ascii(get(p, "code"));
    if (r.chunk.empty() || code.empty()) continue;
    if (code.size() != 1 || code[0] < 'a' || code[0] > 'z') {
      // CUDA v0.6 supports one-key codes only.
      continue;
    }
    r.code = code[0];
    r.scope = parse_scope(get(p, "scope").empty() ? "any" : get(p, "scope"));
    r.enabled = true;
    r.literal = false;
    rules.push_back(r);
  }

  // Add literal fallback rules. These are immutable in mappings.
  for (char c = 'a'; c <= 'z'; ++c) {
    Rule r;
    r.rule_id = std::string("literal_") + c;
    r.chunk = std::string(1, c);
    r.code = c;
    r.scope = SCOPE_ANY;
    r.enabled = true;
    r.literal = true;
    rules.push_back(r);
  }

  std::sort(rules.begin(), rules.end(), [](const Rule& a, const Rule& b) {
    if (a.chunk.size() != b.chunk.size()) return a.chunk.size() > b.chunk.size();
    if (a.chunk != b.chunk) return a.chunk < b.chunk;
    return a.rule_id < b.rule_id;
  });

  return rules;
}

static std::vector<Word> load_lexicon(const std::string& path) {
  std::ifstream f(path);
  if (!f) throw std::runtime_error("cannot open lexicon: " + path);
  std::map<std::string, int> freq; // sorted alphabetically for stable word_id tie-break
  std::string line;
  while (std::getline(f, line)) {
    if (line.empty() || line[0] == '#') continue;
    std::string word;
    std::string freq_s;
    if (line.find('\t') != std::string::npos) {
      std::stringstream ss(line);
      std::getline(ss, word, '\t');
      std::getline(ss, freq_s, '\t');
    } else {
      std::stringstream ss(line);
      ss >> word >> freq_s;
    }
    word = lower_ascii(word);
    if (!is_ascii_alpha_string(word)) continue;
    int v = 1;
    if (!freq_s.empty()) {
      try { v = std::max(1, std::stoi(freq_s)); } catch (...) { v = 1; }
    }
    freq[word] += v;
  }

  std::vector<Word> words;
  for (auto& kv : freq) {
    words.push_back({kv.first, kv.second});
  }
  return words;
}

static bool rule_matches(const Rule& r, const std::string& word, int pos) {
  if (!r.enabled) return false;
  int n = (int)word.size();
  int L = (int)r.chunk.size();
  if (pos + L > n) return false;
  if (word.compare(pos, L, r.chunk) != 0) return false;

  int end = pos + L;
  switch (r.scope) {
    case SCOPE_ANY: return true;
    case SCOPE_PREFIX: return pos == 0;
    case SCOPE_SUFFIX: return end == n;
    case SCOPE_WHOLE: return pos == 0 && end == n;
  }
  return false;
}

static void enumerate_paths_for_word(
    const std::string& word,
    int word_id,
    const std::vector<Rule>& rules,
    Settings settings,
    std::vector<PathTmp>& out_paths
) {
  int n = (int)word.size();
  std::vector<int> cur;

  std::function<void(int)> dfs = [&](int pos) {
    if ((int)out_paths.size() >= settings.max_paths_per_word + 100000000) {
      return;
    }
    if (pos == n) {
      out_paths.push_back({word_id, cur});
      return;
    }

    int before_count = (int)out_paths.size();
    for (int rid = 0; rid < (int)rules.size(); ++rid) {
      const Rule& r = rules[rid];
      if (rule_matches(r, word, pos)) {
        cur.push_back(rid);
        dfs(pos + (int)r.chunk.size());
        cur.pop_back();
        // Hard cap per word to avoid path explosion.
        if ((int)out_paths.size() - before_count >= settings.max_paths_per_word) break;
      }
    }
  };

  int start = (int)out_paths.size();
  dfs(0);
  int end = (int)out_paths.size();

  // If explosion happened, keep shortest paths first.
  if (end - start > settings.max_paths_per_word) {
    std::sort(out_paths.begin() + start, out_paths.end(), [](const PathTmp& a, const PathTmp& b) {
      if (a.rule_ids.size() != b.rule_ids.size()) return a.rule_ids.size() < b.rule_ids.size();
      return a.rule_ids < b.rule_ids;
    });
    out_paths.erase(out_paths.begin() + start + settings.max_paths_per_word, out_paths.begin() + end);
  }
}

static int literal_cost_char(unsigned char c) {
  return (c < 128) ? 1 : 1;
}

static size_t utf8_char_len(unsigned char c) {
  if (c < 0x80) return 1;
  if ((c >> 5) == 0x6) return 2;
  if ((c >> 4) == 0xE) return 3;
  if ((c >> 3) == 0x1E) return 4;
  return 1;
}

static int uppercase_extra_ascii(const std::string& s) {
  int total = 0;
  for (unsigned char c : s) {
    if (c >= 'A' && c <= 'Z') ++total;
  }
  return total;
}

__host__ __device__ static inline int delim_literal_cost(int d) {
  switch (d) {
    case D_EOF: return 0;
    case D_SPACE: return 1;
    case D_NEWLINE: return 1;
    case D_COMMA:
    case D_PERIOD:
    case D_SEMI:
    case D_COLON:
    case D_QMARK:
    case D_EXCL:
      return 1;
    case D_COMMA_SPACE:
    case D_PERIOD_SPACE:
    case D_SEMI_SPACE:
    case D_COLON_SPACE:
    case D_QMARK_SPACE:
    case D_EXCL_SPACE:
      return 2;
    default:
      return 0;
  }
}

static int classify_delim(const std::string& text, size_t pos, int& consumed_len) {
  consumed_len = 0;
  if (pos >= text.size()) return D_EOF;
  char ch = text[pos];
  if (ch == ' ') { consumed_len = 1; return D_SPACE; }
  if (ch == '\n') { consumed_len = 1; return D_NEWLINE; }

  auto punct_type = [&](int plain, int spaced) -> int {
    if (pos + 1 < text.size() && text[pos + 1] == ' ') {
      consumed_len = 2;
      return spaced;
    }
    consumed_len = 1;
    return plain;
  };

  switch (ch) {
    case ',': return punct_type(D_COMMA, D_COMMA_SPACE);
    case '.': return punct_type(D_PERIOD, D_PERIOD_SPACE);
    case ';': return punct_type(D_SEMI, D_SEMI_SPACE);
    case ':': return punct_type(D_COLON, D_COLON_SPACE);
    case '?': return punct_type(D_QMARK, D_QMARK_SPACE);
    case '!': return punct_type(D_EXCL, D_EXCL_SPACE);
    default:
      consumed_len = 0;
      return D_OTHER;
  }
}

static void preprocess_article(const std::string& article_path, HostData& hd, Settings settings) {
  std::ifstream f(article_path, std::ios::binary);
  if (!f) throw std::runtime_error("cannot open article: " + article_path);
  std::string text((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());

  hd.article_counts.assign(hd.words.size() * D_COUNT, 0);
  hd.literal_base_cost = 0;
  hd.baseline_total = 0;
  hd.uppercase_extra_total = 0;
  for (size_t p = 0; p < text.size();) {
    unsigned char c = static_cast<unsigned char>(text[p]);
    hd.baseline_total += literal_cost_char(c);
    p += utf8_char_len(c);
  }
  hd.uppercase_extra_total = uppercase_extra_ascii(text);
  hd.baseline_total += hd.uppercase_extra_total;
  hd.literal_base_cost += hd.uppercase_extra_total;

  size_t i = 0;
  while (i < text.size()) {
    unsigned char c = text[i];
    if (std::isalpha(c) && c < 128) {
      size_t j = i;
      while (j < text.size() && std::isalpha((unsigned char)text[j]) && (unsigned char)text[j] < 128) {
        ++j;
      }
      std::string word = lower_ascii(text.substr(i, j - i));
      auto it = hd.word_to_id.find(word);
      if (it == hd.word_to_id.end()) {
        // Unknown word: raw fallback cost, and following chars will be handled literally.
        hd.literal_base_cost += settings.raw_prefix_cost + (int)word.size();
        i = j;
      } else {
        int consumed = 0;
        int d = classify_delim(text, j, consumed);
        int wid = it->second;
        hd.article_counts[wid * D_COUNT + d] += 1;
        i = j + consumed;
      }
    } else {
      hd.literal_base_cost += literal_cost_char(c);
      i += utf8_char_len(c);
    }
  }
}

static std::vector<int> load_mapping_batch(
    const std::string& mappings_path,
    const std::vector<Rule>& rules,
    int& num_mappings
) {
  int R = (int)rules.size();
  std::unordered_map<std::string, int> rule_id_to_index;
  for (int i = 0; i < R; ++i) rule_id_to_index[rules[i].rule_id] = i;

  std::vector<int> base(R);
  for (int i = 0; i < R; ++i) base[i] = rules[i].code - 'a';

  if (mappings_path.empty()) {
    num_mappings = 1;
    return base;
  }

  std::ifstream f(mappings_path);
  if (!f) throw std::runtime_error("cannot open mappings: " + mappings_path);

  std::map<std::string, std::vector<std::pair<int, int>>> overrides;
  std::string line;
  bool first = true;
  while (std::getline(f, line)) {
    if (line.empty() || line[0] == '#') continue;
    auto p = split_tab(line);
    if (first && p.size() >= 3 && p[0] == "mapping_id") {
      first = false;
      continue;
    }
    first = false;
    if (p.size() < 3) continue;
    std::string mid = p[0];
    std::string rid = p[1];
    std::string code = lower_ascii(p[2]);
    if (code.size() != 1 || code[0] < 'a' || code[0] > 'z') continue;
    auto it = rule_id_to_index.find(rid);
    if (it == rule_id_to_index.end()) continue;
    overrides[mid].push_back({it->second, code[0] - 'a'});
  }

  num_mappings = (int)overrides.size();
  std::vector<int> mat(num_mappings * R);
  int m = 0;
  for (auto& kv : overrides) {
    std::copy(base.begin(), base.end(), mat.begin() + m * R);
    for (auto& ov : kv.second) {
      // Literal rules remain immutable.
      if (!rules[ov.first].literal) mat[m * R + ov.first] = ov.second;
    }
    ++m;
  }
  return mat;
}

__device__ __forceinline__ uint64_t pack_append(uint64_t code, int len, int key) {
  return code | (uint64_t(key & 31) << (len * 5));
}

__device__ uint64_t encode_path(
    int mapping_id,
    int path_id,
    const int* mapping_rule_key,
    int num_rules,
    const int* path_offsets,
    const int* flat_path_rules
) {
  int start = path_offsets[path_id];
  int end = path_offsets[path_id + 1];
  uint64_t code = 0;
  int len = 0;
  for (int i = start; i < end; ++i) {
    int rid = flat_path_rules[i];
    int key = mapping_rule_key[mapping_id * num_rules + rid];
    code = pack_append(code, len, key);
    ++len;
  }
  // Put length in top bits to distinguish prefixes.
  code |= (uint64_t(len & 63) << 58);
  return code;
}

__device__ int path_code_len(int path_id, const int* path_offsets) {
  return path_offsets[path_id + 1] - path_offsets[path_id];
}

__device__ int commit_cost(int rank, int delim) {
  if (rank == 0) {
    if (delim == D_EOF) return 0;
    if (delim == D_SPACE || delim == D_NEWLINE) return 1;
    if (delim >= D_COMMA && delim <= D_EXCL_SPACE) return 1;
    return 1; // bare commit before other literal
  }
  if (rank == 1 || rank == 2) {
    if (delim == D_EOF) return 1;
    if (delim == D_SPACE) return 1;
    if (delim == D_NEWLINE) return 2;
    if (delim >= D_COMMA && delim <= D_EXCL_SPACE) return 2;
    return 1;
  }
  return 1000000000;
}

__global__ void compute_word_delim_costs_kernel(
    int num_mappings,
    int num_words,
    int num_rules,
    int num_paths,
    int max_rank,
    int raw_prefix_cost,
    const int* mapping_rule_key,
    const int* word_freq,
    const int* word_len,
    const int* word_path_begin,
    const int* word_path_end,
    const int* path_offsets,
    const int* flat_path_rules,
    int* out_costs // [num_mappings * num_words * D_COUNT]
) {
  int idx = blockIdx.x * blockDim.x + threadIdx.x;
  int total = num_mappings * num_words * D_COUNT;
  if (idx >= total) return;

  int d = idx % D_COUNT;
  int tmp = idx / D_COUNT;
  int w = tmp % num_words;
  int m = tmp / num_words;

  int fallback = raw_prefix_cost + word_len[w] + delim_literal_cost(d);
  int best = fallback;

  int pbegin = word_path_begin[w];
  int pend = word_path_end[w];

  for (int p = pbegin; p < pend; ++p) {
    uint64_t code = encode_path(m, p, mapping_rule_key, num_rules, path_offsets, flat_path_rules);
    int rank = 0;

    // Brute-force candidate rank:
    // count unique lexicon words with same code and higher priority.
    for (int ow = 0; ow < num_words; ++ow) {
      if (ow == w) continue;

      bool higher = false;
      if (word_freq[ow] > word_freq[w]) higher = true;
      else if (word_freq[ow] == word_freq[w] && ow < w) higher = true; // word_id is alpha-sorted
      if (!higher) continue;

      bool match = false;
      for (int op = word_path_begin[ow]; op < word_path_end[ow]; ++op) {
        uint64_t ocode = encode_path(m, op, mapping_rule_key, num_rules, path_offsets, flat_path_rules);
        if (ocode == code) {
          match = true;
          break;
        }
      }
      if (match) {
        ++rank;
        if (rank >= max_rank) break;
      }
    }

    if (rank < max_rank) {
      int c = path_code_len(p, path_offsets) + commit_cost(rank, d);
      if (c < best) best = c;
    }
  }

  out_costs[idx] = best;
}

__global__ void reduce_article_costs_kernel(
    int num_mappings,
    int num_words,
    int literal_base_cost,
    const int* article_counts, // [num_words * D_COUNT]
    const int* word_delim_costs,
    int* out_total
) {
  int m = blockIdx.x * blockDim.x + threadIdx.x;
  if (m >= num_mappings) return;

  long long total = literal_base_cost;
  for (int w = 0; w < num_words; ++w) {
    for (int d = 0; d < D_COUNT; ++d) {
      int cnt = article_counts[w * D_COUNT + d];
      if (cnt == 0) continue;
      int c = word_delim_costs[(m * num_words + w) * D_COUNT + d];
      total += (long long)cnt * c;
    }
  }
  out_total[m] = (int)total;
}

static void flatten_paths(HostData& hd) {
  int W = (int)hd.words.size();
  hd.word_path_begin.assign(W, 0);
  hd.word_path_end.assign(W, 0);

  std::vector<std::vector<int>> by_word(W);
  for (int pid = 0; pid < (int)hd.paths.size(); ++pid) {
    by_word[hd.paths[pid].word_id].push_back(pid);
  }

  std::vector<PathTmp> reordered;
  for (int w = 0; w < W; ++w) {
    hd.word_path_begin[w] = (int)reordered.size();
    for (int old_pid : by_word[w]) reordered.push_back(hd.paths[old_pid]);
    hd.word_path_end[w] = (int)reordered.size();
  }
  hd.paths.swap(reordered);

  hd.path_offsets.clear();
  hd.flat_path_rules.clear();
  hd.path_word.clear();
  hd.path_offsets.push_back(0);
  for (auto& p : hd.paths) {
    hd.path_word.push_back(p.word_id);
    for (int rid : p.rule_ids) hd.flat_path_rules.push_back(rid);
    hd.path_offsets.push_back((int)hd.flat_path_rules.size());
  }
}

static void write_summary(const std::string& outdir, const std::vector<int>& costs, int baseline_total) {
  // Prototype restriction: outdir should not contain shell-special characters.
  // The Ninja scripts use simple paths such as out/cuda_sample.
  std::string cmd = "mkdir -p " + outdir;
  std::system(cmd.c_str());

  std::ofstream f(outdir + "/cuda_summary.csv");
  f << "mapping_index,total_cost,baseline_total,saved,reduction_ratio\n";
  for (int i = 0; i < (int)costs.size(); ++i) {
    int saved = baseline_total - costs[i];
    double ratio = baseline_total ? double(saved) / double(baseline_total) : 0.0;
    f << i << "," << costs[i] << "," << baseline_total << "," << saved << "," << ratio << "\n";
  }

  std::ofstream j(outdir + "/cuda_summary.json");
  j << "{\n";
  j << "  \"num_mappings\": " << costs.size() << ",\n";
  j << "  \"baseline_total\": " << baseline_total << ",\n";
  j << "  \"costs\": [";
  for (size_t i = 0; i < costs.size(); ++i) {
    if (i) j << ", ";
    j << costs[i];
  }
  j << "]\n}\n";
}

static std::string arg_value(int argc, char** argv, const std::string& key, const std::string& def = "") {
  for (int i = 1; i + 1 < argc; ++i) {
    if (argv[i] == key) return argv[i + 1];
  }
  return def;
}

int main(int argc, char** argv) {
  for (int ai = 1; ai < argc; ++ai) {
    std::string a = argv[ai];
    if (a == "--help" || a == "-h") {
      std::cout
        << "blockcode_cuda_eval v0.7-ninja\\n"
        << "Usage:\\n"
        << "  blockcode_cuda_eval --rules rules.tsv --lexicon lexicon.tsv --article article.txt [--mappings mappings.tsv] --out outdir\\n";
      return 0;
    }
  }

  std::string rules_path = arg_value(argc, argv, "--rules");
  std::string lexicon_path = arg_value(argc, argv, "--lexicon");
  std::string article_path = arg_value(argc, argv, "--article");
  std::string mappings_path = arg_value(argc, argv, "--mappings");
  std::string outdir = arg_value(argc, argv, "--out", "out/cuda_eval");

  if (rules_path.empty() || lexicon_path.empty() || article_path.empty()) {
    std::cerr << "Usage: blockcode_cuda_eval --rules rules.tsv --lexicon lexicon.tsv --article article.txt [--mappings mappings.tsv] --out outdir\n";
    return 2;
  }

  Settings settings;

  HostData hd;
  hd.rules = load_rules_tsv(rules_path);
  hd.words = load_lexicon(lexicon_path);
  for (int i = 0; i < (int)hd.words.size(); ++i) hd.word_to_id[hd.words[i].text] = i;

  std::cerr << "rules: " << hd.rules.size() << "\n";
  std::cerr << "words: " << hd.words.size() << "\n";

  // Enumerate segmentation templates for every lexicon word.
  for (int w = 0; w < (int)hd.words.size(); ++w) {
    std::vector<PathTmp> paths_w;
    enumerate_paths_for_word(hd.words[w].text, w, hd.rules, settings, paths_w);
    if (paths_w.empty()) {
      // Should not happen due to literal rules.
      std::cerr << "warning: no path for " << hd.words[w].text << "\n";
    }
    hd.paths.insert(hd.paths.end(), paths_w.begin(), paths_w.end());
  }
  flatten_paths(hd);

  std::cerr << "paths: " << hd.paths.size() << "\n";
  std::cerr << "flat path rule ids: " << hd.flat_path_rules.size() << "\n";

  preprocess_article(article_path, hd, settings);

  int num_mappings = 0;
  std::vector<int> mapping_matrix = load_mapping_batch(mappings_path, hd.rules, num_mappings);
  std::cerr << "mappings: " << num_mappings << "\n";
  if (num_mappings <= 0) {
    std::cerr << "error: no valid mappings loaded from --mappings. "
              << "Check TSV line endings, rule_id values, and code column.\n";
    return 3;
  }
  std::cerr << "literal_base_cost: " << hd.literal_base_cost << "\n";
  std::cerr << "baseline_total: " << hd.baseline_total << "\n";

  if (num_mappings <= 0) {
    std::cerr << "error: no valid mappings were loaded. Check mappings TSV columns and line endings.\n";
    return 3;
  }

  int W = (int)hd.words.size();
  int R = (int)hd.rules.size();
  int P = (int)hd.paths.size();

  int *d_mapping = nullptr, *d_word_freq = nullptr, *d_word_len = nullptr;
  int *d_word_path_begin = nullptr, *d_word_path_end = nullptr;
  int *d_path_offsets = nullptr, *d_flat_path_rules = nullptr;
  int *d_article_counts = nullptr, *d_word_delim_costs = nullptr, *d_total = nullptr;

  CUDA_CHECK(cudaMalloc(&d_mapping, sizeof(int) * mapping_matrix.size()));
  CUDA_CHECK(cudaMalloc(&d_word_freq, sizeof(int) * W));
  CUDA_CHECK(cudaMalloc(&d_word_len, sizeof(int) * W));
  CUDA_CHECK(cudaMalloc(&d_word_path_begin, sizeof(int) * W));
  CUDA_CHECK(cudaMalloc(&d_word_path_end, sizeof(int) * W));
  CUDA_CHECK(cudaMalloc(&d_path_offsets, sizeof(int) * hd.path_offsets.size()));
  CUDA_CHECK(cudaMalloc(&d_flat_path_rules, sizeof(int) * hd.flat_path_rules.size()));
  CUDA_CHECK(cudaMalloc(&d_article_counts, sizeof(int) * hd.article_counts.size()));
  CUDA_CHECK(cudaMalloc(&d_word_delim_costs, sizeof(int) * num_mappings * W * D_COUNT));
  CUDA_CHECK(cudaMalloc(&d_total, sizeof(int) * num_mappings));

  std::vector<int> word_freq(W), word_len(W);
  for (int i = 0; i < W; ++i) {
    word_freq[i] = hd.words[i].freq;
    word_len[i] = (int)hd.words[i].text.size();
  }

  CUDA_CHECK(cudaMemcpy(d_mapping, mapping_matrix.data(), sizeof(int) * mapping_matrix.size(), cudaMemcpyHostToDevice));
  CUDA_CHECK(cudaMemcpy(d_word_freq, word_freq.data(), sizeof(int) * W, cudaMemcpyHostToDevice));
  CUDA_CHECK(cudaMemcpy(d_word_len, word_len.data(), sizeof(int) * W, cudaMemcpyHostToDevice));
  CUDA_CHECK(cudaMemcpy(d_word_path_begin, hd.word_path_begin.data(), sizeof(int) * W, cudaMemcpyHostToDevice));
  CUDA_CHECK(cudaMemcpy(d_word_path_end, hd.word_path_end.data(), sizeof(int) * W, cudaMemcpyHostToDevice));
  CUDA_CHECK(cudaMemcpy(d_path_offsets, hd.path_offsets.data(), sizeof(int) * hd.path_offsets.size(), cudaMemcpyHostToDevice));
  CUDA_CHECK(cudaMemcpy(d_flat_path_rules, hd.flat_path_rules.data(), sizeof(int) * hd.flat_path_rules.size(), cudaMemcpyHostToDevice));
  CUDA_CHECK(cudaMemcpy(d_article_counts, hd.article_counts.data(), sizeof(int) * hd.article_counts.size(), cudaMemcpyHostToDevice));

  int total_threads = num_mappings * W * D_COUNT;
  int block = 128;
  int grid = (total_threads + block - 1) / block;

  compute_word_delim_costs_kernel<<<grid, block>>>(
      num_mappings, W, R, P, settings.max_candidate_rank, settings.raw_prefix_cost,
      d_mapping, d_word_freq, d_word_len,
      d_word_path_begin, d_word_path_end,
      d_path_offsets, d_flat_path_rules,
      d_word_delim_costs
  );
  CUDA_CHECK(cudaGetLastError());

  int grid2 = (num_mappings + block - 1) / block;
  reduce_article_costs_kernel<<<grid2, block>>>(
      num_mappings, W, hd.literal_base_cost,
      d_article_counts, d_word_delim_costs, d_total
  );
  CUDA_CHECK(cudaGetLastError());
  CUDA_CHECK(cudaDeviceSynchronize());

  std::vector<int> costs(num_mappings);
  CUDA_CHECK(cudaMemcpy(costs.data(), d_total, sizeof(int) * num_mappings, cudaMemcpyDeviceToHost));

  write_summary(outdir, costs, hd.baseline_total);

  std::cout << "CUDA evaluation complete.\n";
  for (int i = 0; i < num_mappings; ++i) {
    int saved = hd.baseline_total - costs[i];
    double ratio = hd.baseline_total ? double(saved) / double(hd.baseline_total) : 0.0;
    std::cout << "mapping " << i << ": total=" << costs[i]
              << " baseline=" << hd.baseline_total
              << " saved=" << saved
              << " reduction=" << ratio << "\n";
  }

  cudaFree(d_mapping);
  cudaFree(d_word_freq);
  cudaFree(d_word_len);
  cudaFree(d_word_path_begin);
  cudaFree(d_word_path_end);
  cudaFree(d_path_offsets);
  cudaFree(d_flat_path_rules);
  cudaFree(d_article_counts);
  cudaFree(d_word_delim_costs);
  cudaFree(d_total);

  return 0;
}
