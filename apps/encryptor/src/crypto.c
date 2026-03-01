#include "encryptor.h"
#include "crypto.h"

int encrypt_data(unsigned char *data, size_t data_len,
                unsigned char *key,
                unsigned char *additional_data, size_t additional_data_len,
                unsigned char **encrypted, size_t *encrypted_size,
                crypto_algorithm_t algorithm) {
    
    unsigned char nonce[crypto_secretbox_NONCEBYTES];
    size_t total_size;
    
    // Generate random nonce
    randombytes_buf(nonce, sizeof(nonce));
    
    // Calculate total size needed
    total_size = sizeof(nonce) + crypto_secretbox_MACBYTES + data_len;
    
    // Allocate memory for encrypted data
    *encrypted = malloc(total_size);
    if (*encrypted == NULL) {
        return -1;
    }
    
    // Copy nonce to beginning of encrypted data
    memcpy(*encrypted, nonce, sizeof(nonce));
    
    // Encrypt data
    int result = crypto_secretbox_easy(
        *encrypted + sizeof(nonce),
        data,
        data_len,
        nonce,
        key
    );
    
    if (result == 0) {
        *encrypted_size = total_size;
        return 0;
    } else {
        free(*encrypted);
        *encrypted = NULL;
        return -1;
    }
}

int decrypt_data(unsigned char *encrypted_data, size_t encrypted_data_len,
                unsigned char *key,
                unsigned char **decrypted, size_t *decrypted_size,
                crypto_algorithm_t algorithm) {
    
    if (encrypted_data_len < crypto_secretbox_NONCEBYTES + crypto_secretbox_MACBYTES) {
        return -1;
    }
    
    // Extract nonce
    unsigned char *nonce = encrypted_data;
    unsigned char *ciphertext = encrypted_data + crypto_secretbox_NONCEBYTES;
    size_t ciphertext_len = encrypted_data_len - crypto_secretbox_NONCEBYTES;
    
    // Calculate decrypted size
    size_t decrypted_len = ciphertext_len - crypto_secretbox_MACBYTES;
    
    // Allocate memory for decrypted data
    *decrypted = malloc(decrypted_len);
    if (*decrypted == NULL) {
        return -1;
    }
    
    // Decrypt data
    int result = crypto_secretbox_open_easy(
        *decrypted,
        ciphertext,
        ciphertext_len,
        nonce,
        key
    );
    
    if (result == 0) {
        *decrypted_size = decrypted_len;
        return 0;
    } else {
        free(*decrypted);
        *decrypted = NULL;
        return -1;
    }
}
