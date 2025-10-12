#include "encryptor.h"
#include <stdio.h>

void calculate_checksum(unsigned char *data, size_t size, char *checksum) {
    unsigned char hash[crypto_generichash_BYTES];
    
    crypto_generichash(hash, sizeof(hash), data, size, NULL, 0);
    
    // Convert to hex string
    for (size_t i = 0; i < sizeof(hash); i++) {
        sprintf(checksum + (i * 2), "%02x", hash[i]);
    }
    checksum[sizeof(hash) * 2] = '\0';
}
