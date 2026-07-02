/**
 * MiniKernel System Call Bridge
 * 
 * Provides direct access to Linux syscalls from Python
 * Uses ctypes-compatible interface for zero-copy performance
 */

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <unistd.h>
#include <sys/syscall.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <errno.h>
#include <string.h>

/**
 * Execute raw Linux syscall
 * 
 * Args:
 *   syscall_num: Linux syscall number
 *   arg1-arg6: Syscall arguments (long integers)
 * 
 * Returns:
 *   Result of syscall (long integer)
 */
static PyObject* 
minikernel_syscall(PyObject* self, PyObject* args) {
    long syscall_num;
    long arg1 = 0, arg2 = 0, arg3 = 0, arg4 = 0, arg5 = 0, arg6 = 0;
    
    if (!PyArg_ParseTuple(args, "l|llllll", 
        &syscall_num, &arg1, &arg2, &arg3, &arg4, &arg5, &arg6)) {
        return NULL;
    }
    
    // Execute syscall
    long result = syscall(syscall_num, arg1, arg2, arg3, arg4, arg5, arg6);
    
    // Check for error
    if (result == -1) {
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }
    
    return PyLong_FromLong(result);
}

/**
 * Memory map a file or anonymous region
 * 
 * Python-accessible mmap wrapper for direct memory control
 */
static PyObject*
minikernel_mmap(PyObject* self, PyObject* args) {
    int fd = -1;
    size_t length;
    int prot = PROT_READ | PROT_WRITE;
    int flags = MAP_PRIVATE | MAP_ANONYMOUS;
    off_t offset = 0;
    
    if (!PyArg_ParseTuple(args, "n|iiil", &length, &fd, &prot, &flags, &offset)) {
        return NULL;
    }
    
    void* addr = mmap(NULL, length, prot, flags, fd, offset);
    
    if (addr == MAP_FAILED) {
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }
    
    // Return address as Python long
    return PyLong_FromVoidPtr(addr);
}

/**
 * Unmap memory region
 */
static PyObject*
minikernel_munmap(PyObject* self, PyObject* args) {
    void* addr;
    size_t length;
    
    if (!PyArg_ParseTuple(args, "ln", &addr, &length)) {
        return NULL;
    }
    
    if (munmap(addr, length) == -1) {
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }
    
    Py_RETURN_NONE;
}

/**
 * Read from memory address
 */
static PyObject*
minikernel_read_memory(PyObject* self, PyObject* args) {
    void* addr;
    size_t length;
    
    if (!PyArg_ParseTuple(args, "ln", &addr, &length)) {
        return NULL;
    }
    
    return PyBytes_FromStringAndSize((char*)addr, length);
}

/**
 * Write to memory address
 */
static PyObject*
minikernel_write_memory(PyObject* self, PyObject* args) {
    void* addr;
    Py_buffer buffer;
    
    if (!PyArg_ParseTuple(args, "ly*", &addr, &buffer)) {
        return NULL;
    }
    
    memcpy(addr, buffer.buf, buffer.len);
    PyBuffer_Release(&buffer);
    
    Py_RETURN_NONE;
}

/**
 * Set memory protection
 */
static PyObject*
minikernel_mprotect(PyObject* self, PyObject* args) {
    void* addr;
    size_t length;
    int prot;
    
    if (!PyArg_ParseTuple(args, "lni", &addr, &length, &prot)) {
        return NULL;
    }
    
    if (mprotect(addr, length, prot) == -1) {
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }
    
    Py_RETURN_NONE;
}

// Method definitions
static PyMethodDef MiniKernelMethods[] = {
    {"syscall", minikernel_syscall, METH_VARARGS, 
     "Execute raw Linux syscall"},
    {"mmap", minikernel_mmap, METH_VARARGS,
     "Map memory region"},
    {"munmap", minikernel_munmap, METH_VARARGS,
     "Unmap memory region"},
    {"read_memory", minikernel_read_memory, METH_VARARGS,
     "Read from memory address"},
    {"write_memory", minikernel_write_memory, METH_VARARGS,
     "Write to memory address"},
    {"mprotect", minikernel_mprotect, METH_VARARGS,
     "Set memory protection"},
    {NULL, NULL, 0, NULL}
};

// Module definition
static struct PyModuleDef minikernelmodule = {
    PyModuleDef_HEAD_INIT,
    "syscall_bridge",
    "MiniKernel system call bridge for direct hardware access",
    -1,
    MiniKernelMethods
};

// Module initialization
PyMODINIT_FUNC
PyInit_syscall_bridge(void) {
    PyObject* module = PyModule_Create(&minikernelmodule);
    
    if (module == NULL) {
        return NULL;
    }
    
    // Add constants
    PyModule_AddIntConstant(module, "PROT_NONE", PROT_NONE);
    PyModule_AddIntConstant(module, "PROT_READ", PROT_READ);
    PyModule_AddIntConstant(module, "PROT_WRITE", PROT_WRITE);
    PyModule_AddIntConstant(module, "PROT_EXEC", PROT_EXEC);
    
    PyModule_AddIntConstant(module, "MAP_SHARED", MAP_SHARED);
    PyModule_AddIntConstant(module, "MAP_PRIVATE", MAP_PRIVATE);
    PyModule_AddIntConstant(module, "MAP_ANONYMOUS", MAP_ANONYMOUS);
    PyModule_AddIntConstant(module, "MAP_FIXED", MAP_FIXED);
    
    return module;
}
