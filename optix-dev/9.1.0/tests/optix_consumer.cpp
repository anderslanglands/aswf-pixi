#include <optix.h>
#include <optix_function_table_definition.h>
#include <optix_stubs.h>

#ifndef OPTIX_VERSION
#error "OPTIX_VERSION is not defined"
#endif

#if OPTIX_VERSION < 90100 || OPTIX_VERSION >= 90200
#error "Expected OptiX 9.1.x headers"
#endif

int main() {
    OptixDeviceContext context = nullptr;
    OptixDeviceContextOptions options = {};
    auto init_fn = &optixInit;
    auto create_context_fn = &optixDeviceContextCreate;

    (void)context;
    (void)options;
    (void)init_fn;
    (void)create_context_fn;

    return OPTIX_SUCCESS == 0 ? 0 : 1;
}
