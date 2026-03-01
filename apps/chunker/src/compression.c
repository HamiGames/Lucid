#include "chunker.h"
#include "compression.h"

int compress_data(unsigned char *input, size_t input_size,
                 unsigned char *output, size_t *output_size,
                 int compression_level) {
    z_stream stream;
    int result;
    
    // Initialize zlib stream
    stream.zalloc = Z_NULL;
    stream.zfree = Z_NULL;
    stream.opaque = Z_NULL;
    
    result = deflateInit(&stream, compression_level);
    if (result != Z_OK) {
        return result;
    }
    
    // Set input and output
    stream.avail_in = (uInt)input_size;
    stream.next_in = input;
    stream.avail_out = (uInt)(*output_size);
    stream.next_out = output;
    
    // Compress data
    result = deflate(&stream, Z_FINISH);
    
    // Update output size
    *output_size = stream.total_out;
    
    // Cleanup
    deflateEnd(&stream);
    
    return result == Z_STREAM_END ? Z_OK : result;
}

int decompress_data(unsigned char *input, size_t input_size,
                   unsigned char *output, size_t *output_size) {
    z_stream stream;
    int result;
    
    // Initialize zlib stream
    stream.zalloc = Z_NULL;
    stream.zfree = Z_NULL;
    stream.opaque = Z_NULL;
    
    result = inflateInit(&stream);
    if (result != Z_OK) {
        return result;
    }
    
    // Set input and output
    stream.avail_in = (uInt)input_size;
    stream.next_in = input;
    stream.avail_out = (uInt)(*output_size);
    stream.next_out = output;
    
    // Decompress data
    result = inflate(&stream, Z_FINISH);
    
    // Update output size
    *output_size = stream.total_out;
    
    // Cleanup
    inflateEnd(&stream);
    
    return result == Z_STREAM_END ? Z_OK : result;
}
