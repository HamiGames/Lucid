#include "chunker.h"
#include <openssl/sha.h>
#include <string.h>

void calculate_checksum(unsigned char *data, size_t size, char *checksum) {
    unsigned char hash[SHA256_DIGEST_LENGTH];
    SHA256_CTX sha256;
    
    SHA256_Init(&sha256);
    SHA256_Update(&sha256, data, size);
    SHA256_Final(hash, &sha256);
    
    // Convert to hex string
    for (int i = 0; i < SHA256_DIGEST_LENGTH; i++) {
        sprintf(checksum + (i * 2), "%02x", hash[i]);
    }
    checksum[SHA256_DIGEST_LENGTH * 2] = '\0';
}
