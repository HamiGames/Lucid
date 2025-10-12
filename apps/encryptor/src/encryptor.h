#ifndef ENCRYPTOR_H
#define ENCRYPTOR_H

#include <Python.h>
#include <sodium.h>

// Algorithm types
typedef enum {
    CRYPTO_XCHACHA20_POLY1305 = 0,
    CRYPTO_CHACHA20_POLY1305 = 1,
    CRYPTO_AES256_GCM = 2,
    CRYPTO_SALSA20_POLY1305 = 3
} crypto_algorithm_t;

// Function declarations
int encrypt_data(unsigned char *data, size_t data_len,
                unsigned char *key,
                unsigned char *additional_data, size_t additional_data_len,
                unsigned char **encrypted, size_t *encrypted_size,
                crypto_algorithm_t algorithm);

int decrypt_data(unsigned char *encrypted_data, size_t encrypted_data_len,
                unsigned char *key,
                unsigned char **decrypted, size_t *decrypted_size,
                crypto_algorithm_t algorithm);

void calculate_checksum(unsigned char *data, size_t size, char *checksum);

#endif // ENCRYPTOR_H
