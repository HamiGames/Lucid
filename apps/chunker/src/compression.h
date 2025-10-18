#ifndef COMPRESSION_H
#define COMPRESSION_H

#include <zlib.h>

// Function declarations for compression utilities
int compress_data(unsigned char *input, size_t input_size,
                 unsigned char *output, size_t *output_size,
                 int compression_level);

int decompress_data(unsigned char *input, size_t input_size,
                   unsigned char *output, size_t *output_size);

#endif // COMPRESSION_H
