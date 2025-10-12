#ifndef CHUNKER_H
#define CHUNKER_H

#include <Python.h>
#include <numpy/arrayobject.h>
#include <zlib.h>

// Constants
#define MAX_CHUNK_SIZE (100 * 1024 * 1024)  // 100MB max chunk size
#define DEFAULT_COMPRESSION_LEVEL 6

// Function declarations
int compress_data(unsigned char *input, size_t input_size,
                 unsigned char *output, size_t *output_size,
                 int compression_level);

int decompress_data(unsigned char *input, size_t input_size,
                   unsigned char *output, size_t *output_size);

void calculate_checksum(unsigned char *data, size_t size, char *checksum);

#endif // CHUNKER_H
