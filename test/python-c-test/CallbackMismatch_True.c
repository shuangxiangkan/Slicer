// CallbackMismatch / correct
#include <Python.h>
#include <stdio.h>

static unsigned long g_counter = 0;
static void log_b() {}

static PyObject *py_tick(PyObject *self, PyObject *args) {
  long k = 0;
  if (!PyArg_ParseTuple(args, "l", &k))
    return NULL;
  g_counter += (unsigned long)k;
  Py_RETURN_NONE;
}
static PyMethodDef HostMethods[] = {{"tick", py_tick, METH_VARARGS, ""},
                                    {NULL, NULL, 0, NULL}};
static struct PyModuleDef HostModule = {PyModuleDef_HEAD_INIT, "host", NULL, -1,
                                        HostMethods};
PyMODINIT_FUNC PyInit_host(void) { return PyModule_Create(&HostModule); }

int main() {
  PyImport_AppendInittab("host", &PyInit_host);
  Py_Initialize();
  PyObject *g = PyModule_GetDict(PyImport_AddModule("__main__"));
  const char *py = "import host\n"
                   "def add(a,b,k):\n"
                   "    print('P')\n"
                   "    host.tick(k)\n"
                   "    return a+b\n";
  PyRun_String(py, Py_file_input, g, g);

  PyObject *fn = PyDict_GetItemString(g, "add");
  PyObject *args = Py_BuildValue("(iii)", 1, 2, 7);
  PyObject *ret = PyObject_CallObject(fn, args);

  if (!ret) {
    PyErr_Print();
    Py_Finalize();
    return 1;
  }
  long v = PyLong_AsLong(ret);
  printf("OK:%ld COUNT:%lu\n", v, g_counter);
  Py_DECREF(ret);
  Py_Finalize();
  return 0;
}
