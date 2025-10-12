#ifndef CRYPTO_H
#define CRYPTO_H

#include <sodium.h>

// Function declarations for cryptographic operations
int encrypt_data(unsigned char *data, size_t data_len,
                unsigned char *key,
                unsigned char *additional_data, size_t additional_data_len,
                unsigned char **encrypted, size_t *encrypted_size,
                crypto_algorithm_t algorithm);

int decrypt_data(unsigned char *encrypted_data, size_t encrypted_data_len,
                unsigned char *key,
                unsigned char **decrypted, size_t *decrypted_size,
                crypto_algorithm_t algorithm);

#endif // CRYPTO_H
