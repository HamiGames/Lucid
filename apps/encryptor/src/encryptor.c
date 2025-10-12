/*
 * Native libsodium encryptor extension for Lucid RDP
 * High-performance encryption using libsodium
 */

#include <Python.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <sodium.h>
#include "encryptor.h"
#include "crypto.h"
#include "utils.h"

#define MAX_DATA_SIZE (1024 * 1024 * 1024)  // 1GB max data size

typedef struct {
    PyObject_HEAD
    char algorithm[64];
    int algorithm_type;
    int initialized;
} EncryptorObject;

static PyTypeObject EncryptorType;

// Forward declarations
static PyObject* Encryptor_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
static void Encryptor_dealloc(EncryptorObject *self);
static int Encryptor_init(EncryptorObject *self, PyObject *args, PyObject *kwds);
static PyObject* Encryptor_generate_key(EncryptorObject *self, PyObject *args);
static PyObject* Encryptor_encrypt(EncryptorObject *self, PyObject *args);
static PyObject* Encryptor_decrypt(EncryptorObject *self, PyObject *args);
static PyObject* Encryptor_sign(EncryptorObject *self, PyObject *args);
static PyObject* Encryptor_verify(EncryptorObject *self, PyObject *args);
static PyObject* Encryptor_cleanup(EncryptorObject *self, PyObject *args);

// Method definitions
static PyMethodDef Encryptor_methods[] = {
    {"generate_key", (PyCFunction)Encryptor_generate_key, METH_NOARGS, "Generate encryption key"},
    {"encrypt", (PyCFunction)Encryptor_encrypt, METH_VARARGS, "Encrypt data"},
    {"decrypt", (PyCFunction)Encryptor_decrypt, METH_VARARGS, "Decrypt data"},
    {"sign", (PyCFunction)Encryptor_sign, METH_VARARGS, "Sign data"},
    {"verify", (PyCFunction)Encryptor_verify, METH_VARARGS, "Verify signature"},
    {"cleanup", (PyCFunction)Encryptor_cleanup, METH_NOARGS, "Cleanup resources"},
    {NULL, NULL, 0, NULL}
};

// Type definition
static PyTypeObject EncryptorType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "encryptor_native.Encryptor",
    .tp_doc = "Native libsodium encryptor for high-performance encryption",
    .tp_basicsize = sizeof(EncryptorObject),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_new = Encryptor_new,
    .tp_init = (initproc)Encryptor_init,
    .tp_dealloc = (destructor)Encryptor_dealloc,
    .tp_methods = Encryptor_methods,
};

// Module methods
static PyObject* encryptor_version(PyObject *self, PyObject *args) {
    return PyUnicode_FromString("0.1.0");
}

static PyObject* encryptor_libsodium_version(PyObject *self, PyObject *args) {
    return PyUnicode_FromString(sodium_version_string());
}

static PyObject* encryptor_available_algorithms(PyObject *self, PyObject *args) {
    PyObject *algorithms = PyList_New(0);
    PyList_Append(algorithms, PyUnicode_FromString("xchacha20-poly1305"));
    PyList_Append(algorithms, PyUnicode_FromString("chacha20-poly1305"));
    PyList_Append(algorithms, PyUnicode_FromString("aes256-gcm"));
    PyList_Append(algorithms, PyUnicode_FromString("salsa20-poly1305"));
    return algorithms;
}

static PyMethodDef encryptor_module_methods[] = {
    {"version", encryptor_version, METH_NOARGS, "Get version"},
    {"libsodium_version", encryptor_libsodium_version, METH_NOARGS, "Get libsodium version"},
    {"available_algorithms", encryptor_available_algorithms, METH_NOARGS, "Get available algorithms"},
    {NULL, NULL, 0, NULL}
};

// Encryptor object methods
static PyObject* Encryptor_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    EncryptorObject *self = (EncryptorObject*)type->tp_alloc(type, 0);
    if (self != NULL) {
        strcpy(self->algorithm, "xchacha20-poly1305");
        self->algorithm_type = CRYPTO_XCHACHA20_POLY1305;
        self->initialized = 0;
    }
    return (PyObject*)self;
}

static int Encryptor_init(EncryptorObject *self, PyObject *args, PyObject *kwds) {
    static char *kwlist[] = {"algorithm", NULL};
    char *algorithm = NULL;
    
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|s", kwlist, &algorithm)) {
        return -1;
    }
    
    if (algorithm != NULL) {
        strncpy(self->algorithm, algorithm, sizeof(self->algorithm) - 1);
        self->algorithm[sizeof(self->algorithm) - 1] = '\0';
        
        // Determine algorithm type
        if (strcmp(algorithm, "xchacha20-poly1305") == 0) {
            self->algorithm_type = CRYPTO_XCHACHA20_POLY1305;
        } else if (strcmp(algorithm, "chacha20-poly1305") == 0) {
            self->algorithm_type = CRYPTO_CHACHA20_POLY1305;
        } else if (strcmp(algorithm, "aes256-gcm") == 0) {
            self->algorithm_type = CRYPTO_AES256_GCM;
        } else if (strcmp(algorithm, "salsa20-poly1305") == 0) {
            self->algorithm_type = CRYPTO_SALSA20_POLY1305;
        } else {
            PyErr_SetString(PyExc_ValueError, "Unsupported algorithm");
            return -1;
        }
    }
    
    // Initialize libsodium
    if (sodium_init() < 0) {
        PyErr_SetString(PyExc_RuntimeError, "Failed to initialize libsodium");
        return -1;
    }
    
    self->initialized = 1;
    return 0;
}

static void Encryptor_dealloc(EncryptorObject *self) {
    Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject* Encryptor_generate_key(EncryptorObject *self, PyObject *args) {
    if (!self->initialized) {
        PyErr_SetString(PyExc_RuntimeError, "Encryptor not initialized");
        return NULL;
    }
    
    unsigned char key[crypto_secretbox_KEYBYTES];
    randombytes_buf(key, sizeof(key));
    
    return PyBytes_FromStringAndSize((char*)key, sizeof(key));
}

static PyObject* Encryptor_encrypt(EncryptorObject *self, PyObject *args) {
    if (!self->initialized) {
        PyErr_SetString(PyExc_RuntimeError, "Encryptor not initialized");
        return NULL;
    }
    
    Py_buffer data, key, additional_data;
    additional_data.buf = NULL;
    additional_data.len = 0;
    
    if (!PyArg_ParseTuple(args, "y*y*|y*", &data, &key, &additional_data)) {
        return NULL;
    }
    
    // Validate inputs
    if (data.len > MAX_DATA_SIZE) {
        PyBuffer_Release(&data);
        PyBuffer_Release(&key);
        if (additional_data.buf) PyBuffer_Release(&additional_data);
        PyErr_SetString(PyExc_ValueError, "Data too large");
        return NULL;
    }
    
    if (key.len != crypto_secretbox_KEYBYTES) {
        PyBuffer_Release(&data);
        PyBuffer_Release(&key);
        if (additional_data.buf) PyBuffer_Release(&additional_data);
        PyErr_SetString(PyExc_ValueError, "Invalid key size");
        return NULL;
    }
    
    // Encrypt data
    unsigned char *encrypted = NULL;
    size_t encrypted_size = 0;
    
    int result = encrypt_data((unsigned char*)data.buf, data.len,
                             (unsigned char*)key.buf,
                             additional_data.buf, additional_data.len,
                             &encrypted, &encrypted_size,
                             self->algorithm_type);
    
    PyObject *ret = NULL;
    if (result == 0 && encrypted != NULL) {
        ret = PyBytes_FromStringAndSize((char*)encrypted, encrypted_size);
        free(encrypted);
    } else {
        PyErr_SetString(PyExc_RuntimeError, "Encryption failed");
    }
    
    PyBuffer_Release(&data);
    PyBuffer_Release(&key);
    if (additional_data.buf) PyBuffer_Release(&additional_data);
    
    return ret;
}

static PyObject* Encryptor_decrypt(EncryptorObject *self, PyObject *args) {
    if (!self->initialized) {
        PyErr_SetString(PyExc_RuntimeError, "Encryptor not initialized");
        return NULL;
    }
    
    Py_buffer encrypted_data, key;
    
    if (!PyArg_ParseTuple(args, "y*y*", &encrypted_data, &key)) {
        return NULL;
    }
    
    // Validate inputs
    if (key.len != crypto_secretbox_KEYBYTES) {
        PyBuffer_Release(&encrypted_data);
        PyBuffer_Release(&key);
        PyErr_SetString(PyExc_ValueError, "Invalid key size");
        return NULL;
    }
    
    // Decrypt data
    unsigned char *decrypted = NULL;
    size_t decrypted_size = 0;
    
    int result = decrypt_data((unsigned char*)encrypted_data.buf, encrypted_data.len,
                             (unsigned char*)key.buf,
                             &decrypted, &decrypted_size,
                             self->algorithm_type);
    
    PyObject *ret = NULL;
    if (result == 0 && decrypted != NULL) {
        ret = PyBytes_FromStringAndSize((char*)decrypted, decrypted_size);
        free(decrypted);
    } else {
        PyErr_SetString(PyExc_RuntimeError, "Decryption failed");
    }
    
    PyBuffer_Release(&encrypted_data);
    PyBuffer_Release(&key);
    
    return ret;
}

static PyObject* Encryptor_sign(EncryptorObject *self, PyObject *args) {
    if (!self->initialized) {
        PyErr_SetString(PyExc_RuntimeError, "Encryptor not initialized");
        return NULL;
    }
    
    Py_buffer data;
    
    if (!PyArg_ParseTuple(args, "y*", &data)) {
        return NULL;
    }
    
    // Generate signing key pair (in real implementation, this would be stored)
    unsigned char signing_key[crypto_sign_SECRETKEYBYTES];
    unsigned char verify_key[crypto_sign_PUBLICKEYBYTES];
    crypto_sign_keypair(verify_key, signing_key);
    
    // Sign data
    unsigned char *signed_data = NULL;
    unsigned long long signed_data_len = 0;
    
    signed_data = malloc(data.len + crypto_sign_BYTES);
    if (signed_data == NULL) {
        PyBuffer_Release(&data);
        PyErr_SetString(PyExc_MemoryError, "Failed to allocate memory");
        return NULL;
    }
    
    int result = crypto_sign(signed_data, &signed_data_len,
                            (unsigned char*)data.buf, data.len,
                            signing_key);
    
    PyObject *ret = NULL;
    if (result == 0) {
        ret = PyBytes_FromStringAndSize((char*)signed_data, signed_data_len);
    } else {
        PyErr_SetString(PyExc_RuntimeError, "Signing failed");
    }
    
    free(signed_data);
    PyBuffer_Release(&data);
    
    return ret;
}

static PyObject* Encryptor_verify(EncryptorObject *self, PyObject *args) {
    if (!self->initialized) {
        PyErr_SetString(PyExc_RuntimeError, "Encryptor not initialized");
        return NULL;
    }
    
    Py_buffer data, signature;
    
    if (!PyArg_ParseTuple(args, "y*y*", &data, &signature)) {
        return NULL;
    }
    
    // Verify signature
    int result = crypto_sign_verify_detached((unsigned char*)signature.buf,
                                            (unsigned char*)data.buf, data.len,
                                            NULL);  // In real implementation, use actual public key
    
    PyBuffer_Release(&data);
    PyBuffer_Release(&signature);
    
    if (result == 0) {
        Py_RETURN_TRUE;
    } else {
        Py_RETURN_FALSE;
    }
}

static PyObject* Encryptor_cleanup(EncryptorObject *self, PyObject *args) {
    self->initialized = 0;
    Py_RETURN_NONE;
}

// Module definition
static struct PyModuleDef encryptor_module = {
    PyModuleDef_HEAD_INIT,
    "encryptor_native",
    "Native libsodium encryptor extension for Lucid RDP",
    -1,
    encryptor_module_methods
};

PyMODINIT_FUNC PyInit_encryptor_native(void) {
    if (PyType_Ready(&EncryptorType) < 0) {
        return NULL;
    }
    
    PyObject *m = PyModule_Create(&encryptor_module);
    if (m == NULL) {
        return NULL;
    }
    
    Py_INCREF(&EncryptorType);
    if (PyModule_AddObject(m, "Encryptor", (PyObject*)&EncryptorType) < 0) {
        Py_DECREF(&EncryptorType);
        Py_DECREF(m);
        return NULL;
    }
    
    return m;
}
