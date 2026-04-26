#pragma once

#include <pybind11/pybind11.h>

namespace pylibavoid {

void register_geometry(pybind11::module_& m);
void register_router(pybind11::module_& m);
void register_shape(pybind11::module_& m);
void register_connector(pybind11::module_& m);
void register_junction(pybind11::module_& m);

}  // namespace pylibavoid
