/*
 * Native chunker extension for Lucid RDP
 * High-performance data chunking and compression
 */

#include <Python.h>
#include <numpy/arrayobject.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <zlib.h>
#include "chunker.h"
#include "compression.h"
#include "utils.h"

#define MAX_CHUNK_SIZE (100 * 1024 * 1024)  // 100MB max chunk size

typedef struct {
    PyObject_HEAD
    size_t chunk_size;
    int compression_level;
    z_stream zstream;
    int zstream_initialized;
} ChunkerObject;

static PyTypeObject ChunkerType;

// Forward declarations
static PyObject* Chunker_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
static void Chunker_dealloc(ChunkerObject *self);
static int Chunker_init(ChunkerObject *self, PyObject *args, PyObject *kwds);
static PyObject* Chunker_chunk(ChunkerObject *self, PyObject *args);
static PyObject* Chunker_decompress(ChunkerObject *self, PyObject *args);
static PyObject* Chunker_cleanup(ChunkerObject *self, PyObject *args);

// Method definitions
static PyMethodDef Chunker_methods[] = {
    {"chunk", (PyCFunction)Chunker_chunk, METH_VARARGS, "Chunk and compress data"},
    {"decompress", (PyCFunction)Chunker_decompress, METH_VARARGS, "Decompress data"},
    {"cleanup", (PyCFunction)Chunker_cleanup, METH_NOARGS, "Cleanup resources"},
    {NULL, NULL, 0, NULL}
};

// Type definition
static PyTypeObject ChunkerType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "chunker_native.Chunker",
    .tp_doc = "Native chunker for high-performance data processing",
    .tp_basicsize = sizeof(ChunkerObject),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_new = Chunker_new,
    .tp_init = (initproc)Chunker_init,
    .tp_dealloc = (destructor)Chunker_dealloc,
    .tp_methods = Chunker_methods,
};

// Module methods
static PyObject* chunker_version(PyObject *self, PyObject *args) {
    return PyUnicode_FromString("0.1.0");
}

static PyObject* chunker_compress_data(PyObject *self, PyObject *args) {
    Py_buffer data;
    int compression_level = 6;
    
    if (!PyArg_ParseTuple(args, "y*|i", &data, &compression_level)) {
        return NULL;
    }
    
    // Compress data using zlib
    size_t compressed_size = data.len * 2;  // Estimate compressed size
    char *compressed = malloc(compressed_size);
    if (!compressed) {
        PyBuffer_Release(&data);
        PyErr_SetString(PyExc_MemoryError, "Failed to allocate memory for compression");
        return NULL;
    }
    
    int result = compress_data((unsigned char*)data.buf, data.len, 
                              (unsigned char*)compressed, &compressed_size, 
                              compression_level);
    
    PyObject *ret = NULL;
    if (result == Z_OK) {
        ret = PyBytes_FromStringAndSize(compressed, compressed_size);
    } else {
        PyErr_SetString(PyExc_RuntimeError, "Compression failed");
    }
    
    free(compressed);
    PyBuffer_Release(&data);
    return ret;
}

static PyObject* chunker_decompress_data(PyObject *self, PyObject *args) {
    Py_buffer data;
    
    if (!PyArg_ParseTuple(args, "y*", &data)) {
        return NULL;
    }
    
    // Decompress data using zlib
    size_t decompressed_size = data.len * 4;  // Estimate decompressed size
    char *decompressed = malloc(decompressed_size);
    if (!decompressed) {
        PyBuffer_Release(&data);
        PyErr_SetString(PyExc_MemoryError, "Failed to allocate memory for decompression");
        return NULL;
    }
    
    int result = decompress_data((unsigned char*)data.buf, data.len,
                                (unsigned char*)decompressed, &decompressed_size);
    
    PyObject *ret = NULL;
    if (result == Z_OK) {
        ret = PyBytes_FromStringAndSize(decompressed, decompressed_size);
    } else {
        PyErr_SetString(PyExc_RuntimeError, "Decompression failed");
    }
    
    free(decompressed);
    PyBuffer_Release(&data);
    return ret;
}

static PyMethodDef chunker_module_methods[] = {
    {"version", chunker_version, METH_NOARGS, "Get version"},
    {"compress_data", chunker_compress_data, METH_VARARGS, "Compress data"},
    {"decompress_data", chunker_decompress_data, METH_VARARGS, "Decompress data"},
    {NULL, NULL, 0, NULL}
};

// Chunker object methods
static PyObject* Chunker_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    ChunkerObject *self = (ChunkerObject*)type->tp_alloc(type, 0);
    if (self != NULL) {
        self->chunk_size = 8 * 1024 * 1024;  // Default 8MB
        self->compression_level = 6;
        self->zstream_initialized = 0;
    }
    return (PyObject*)self;
}

static int Chunker_init(ChunkerObject *self, PyObject *args, PyObject *kwds) {
    static char *kwlist[] = {"chunk_size", "compression_level", NULL};
    
    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|ki", kwlist,
                                     &self->chunk_size, &self->compression_level)) {
        return -1;
    }
    
    // Validate parameters
    if (self->chunk_size <= 0 || self->chunk_size > MAX_CHUNK_SIZE) {
        PyErr_SetString(PyExc_ValueError, "Invalid chunk size");
        return -1;
    }
    
    if (self->compression_level < 0 || self->compression_level > 9) {
        PyErr_SetString(PyExc_ValueError, "Invalid compression level");
        return -1;
    }
    
    // Initialize zlib stream
    self->zstream.zalloc = Z_NULL;
    self->zstream.zfree = Z_NULL;
    self->zstream.opaque = Z_NULL;
    
    if (deflateInit(&self->zstream, self->compression_level) == Z_OK) {
        self->zstream_initialized = 1;
    } else {
        PyErr_SetString(PyExc_RuntimeError, "Failed to initialize zlib stream");
        return -1;
    }
    
    return 0;
}

static void Chunker_dealloc(ChunkerObject *self) {
    if (self->zstream_initialized) {
        deflateEnd(&self->zstream);
    }
    Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject* Chunker_chunk(ChunkerObject *self, PyObject *args) {
    Py_buffer data;
    
    if (!PyArg_ParseTuple(args, "y*", &data)) {
        return NULL;
    }
    
    // Check if data is too large
    if (data.len > MAX_CHUNK_SIZE) {
        PyBuffer_Release(&data);
        PyErr_SetString(PyExc_ValueError, "Data too large for chunking");
        return NULL;
    }
    
    // Compress the data
    size_t compressed_size = data.len * 2;  // Estimate
    char *compressed = malloc(compressed_size);
    if (!compressed) {
        PyBuffer_Release(&data);
        PyErr_SetString(PyExc_MemoryError, "Failed to allocate memory");
        return NULL;
    }
    
    int result = compress_data((unsigned char*)data.buf, data.len,
                              (unsigned char*)compressed, &compressed_size,
                              self->compression_level);
    
    PyObject *ret = NULL;
    if (result == Z_OK) {
        // Create result dictionary
        ret = PyDict_New();
        if (ret) {
            PyDict_SetItemString(ret, "data", 
                                PyBytes_FromStringAndSize(compressed, compressed_size));
            PyDict_SetItemString(ret, "algorithm", PyUnicode_FromString("zlib"));
            PyDict_SetItemString(ret, "checksum", 
                                PyUnicode_FromString("sha256_hash_here"));  // TODO: Implement
        }
    } else {
        PyErr_SetString(PyExc_RuntimeError, "Chunking failed");
    }
    
    free(compressed);
    PyBuffer_Release(&data);
    return ret;
}

static PyObject* Chunker_decompress(ChunkerObject *self, PyObject *args) {
    Py_buffer data;
    
    if (!PyArg_ParseTuple(args, "y*", &data)) {
        return NULL;
    }
    
    // Decompress the data
    size_t decompressed_size = data.len * 4;  // Estimate
    char *decompressed = malloc(decompressed_size);
    if (!decompressed) {
        PyBuffer_Release(&data);
        PyErr_SetString(PyExc_MemoryError, "Failed to allocate memory");
        return NULL;
    }
    
    int result = decompress_data((unsigned char*)data.buf, data.len,
                                (unsigned char*)decompressed, &decompressed_size);
    
    PyObject *ret = NULL;
    if (result == Z_OK) {
        ret = PyBytes_FromStringAndSize(decompressed, decompressed_size);
    } else {
        PyErr_SetString(PyExc_RuntimeError, "Decompression failed");
    }
    
    free(decompressed);
    PyBuffer_Release(&data);
    return ret;
}

static PyObject* Chunker_cleanup(ChunkerObject *self, PyObject *args) {
    if (self->zstream_initialized) {
        deflateEnd(&self->zstream);
        self->zstream_initialized = 0;
    }
    Py_RETURN_NONE;
}

// Module definition
static struct PyModuleDef chunker_module = {
    PyModuleDef_HEAD_INIT,
    "chunker_native",
    "Native chunker extension for Lucid RDP",
    -1,
    chunker_module_methods
};

PyMODINIT_FUNC PyInit_chunker_native(void) {
    import_array();
    
    if (PyType_Ready(&ChunkerType) < 0) {
        return NULL;
    }
    
    PyObject *m = PyModule_Create(&chunker_module);
    if (m == NULL) {
        return NULL;
    }
    
    Py_INCREF(&ChunkerType);
    if (PyModule_AddObject(m, "Chunker", (PyObject*)&ChunkerType) < 0) {
        Py_DECREF(&ChunkerType);
        Py_DECREF(m);
        return NULL;
    }
    
    return m;
}
