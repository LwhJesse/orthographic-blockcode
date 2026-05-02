// Sketch only. Not compiled by default.
// The key principle: GPU receives integer templates, not raw strings.

#include <stdint.h>

struct MappingView {
    const uint8_t* chunk_to_key; // [num_mappings * num_chunks]
    int num_chunks;
};

struct PathView {
    const int* offsets;   // [num_paths + 1]
    const int* chunks;    // flattened chunk ids
    const int* word_ids;  // [num_paths]
};

struct Entry {
    int mapping_id;
    uint64_t packed_code;
    int code_len;
    int word_id;
    int path_id;
};

__device__ uint64_t pack_append(uint64_t code, int len, uint8_t key) {
    return code | (uint64_t(key & 31) << (len * 5));
}

__global__ void encode_paths_kernel(
    MappingView mappings,
    PathView paths,
    int num_mappings,
    int num_paths,
    Entry* out_entries
) {
    int global = blockIdx.x * blockDim.x + threadIdx.x;
    int total = num_mappings * num_paths;
    if (global >= total) return;

    int mid = global / num_paths;
    int pid = global % num_paths;

    int start = paths.offsets[pid];
    int end = paths.offsets[pid + 1];

    uint64_t packed = 0;
    int len = 0;
    for (int i = start; i < end; ++i) {
        int chunk_id = paths.chunks[i];
        uint8_t key = mappings.chunk_to_key[mid * mappings.num_chunks + chunk_id];
        packed = pack_append(packed, len, key);
        ++len;
    }

    out_entries[global] = Entry{mid, packed, len, paths.word_ids[pid], pid};
}
