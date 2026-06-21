#include <mi/base.h>
#include <mi/mdl/mdl_code_generators.h>
#include <mi/mdl_sdk.h>
#include <mi/neuraylib/imdl_backend.h>
#include <mi/neuraylib/imdl_backend_api.h>
#include <mi/neuraylib/ineuray.h>

#include <cstdlib>
#include <iostream>

#if defined(_WIN32)
#include <windows.h>
#else
#include <dlfcn.h>
#endif

namespace
{

class Shared_library
{
public:
    explicit Shared_library(const char* path) : path_(path)
    {
#if defined(_WIN32)
        handle_ = LoadLibraryA(path);
#else
        handle_ = dlopen(path, RTLD_NOW | RTLD_LOCAL);
#endif
        if (!handle_) {
            std::cerr << "Failed to load " << path_ << load_error() << "\n";
        }
    }

    ~Shared_library()
    {
#if defined(_WIN32)
        if (handle_) {
            FreeLibrary(handle_);
        }
#else
        if (handle_) {
            dlclose(handle_);
        }
#endif
    }

    Shared_library(const Shared_library&) = delete;
    Shared_library& operator=(const Shared_library&) = delete;

    explicit operator bool() const { return handle_ != nullptr; }

    void* symbol(const char* name) const
    {
        if (!handle_) {
            return nullptr;
        }
#if defined(_WIN32)
        void* result = reinterpret_cast<void*>(GetProcAddress(handle_, name));
#else
        dlerror();
        void* result = dlsym(handle_, name);
#endif
        if (!result) {
            std::cerr << "Missing symbol " << name << " in " << path_ << load_error() << "\n";
        }
        return result;
    }

private:
    static const char* load_error()
    {
#if defined(_WIN32)
        return "";
#else
        const char* error = dlerror();
        return error ? error : "";
#endif
    }

    const char* path_ = nullptr;
#if defined(_WIN32)
    HMODULE handle_ = nullptr;
#else
    void* handle_ = nullptr;
#endif
};

bool check_mdl_sdk_factory()
{
    Shared_library sdk_library(MDL_SDK_LIBRARY_PATH);
    if (!sdk_library) {
        return false;
    }

    void* factory_symbol = sdk_library.symbol("mi_factory");
    if (!factory_symbol) {
        return false;
    }

    mi::base::Handle<mi::neuraylib::INeuray> neuray(
        mi::neuraylib::mi_factory<mi::neuraylib::INeuray>(factory_symbol));
    if (!neuray) {
        std::cerr << "mi_factory did not return INeuray\n";
        return false;
    }

    if (neuray->start() != 0) {
        std::cerr << "INeuray::start() failed\n";
        return false;
    }

    mi::base::Handle<mi::neuraylib::IMdl_backend_api> backend_api(
        neuray->get_api_component<mi::neuraylib::IMdl_backend_api>());
    if (!backend_api) {
        std::cerr << "IMdl_backend_api is not available\n";
        neuray->shutdown();
        return false;
    }

    mi::base::Handle<mi::neuraylib::IMdl_backend> ptx_backend(
        backend_api->get_backend(mi::neuraylib::IMdl_backend_api::MB_CUDA_PTX));
    if (!ptx_backend) {
        std::cerr << "CUDA PTX backend is not available\n";
        neuray->shutdown();
        return false;
    }

    ptx_backend.reset();
    backend_api.reset();
    if (neuray->shutdown() != 0) {
        std::cerr << "INeuray::shutdown() failed\n";
        return false;
    }
    return true;
}

bool check_mdl_core_factory()
{
    Shared_library core_library(MDL_CORE_LIBRARY_PATH);
    if (!core_library) {
        return false;
    }
    return core_library.symbol("mi_mdl_factory") != nullptr;
}

} // namespace

int main()
{
    static_assert(mi::neuraylib::IMdl_backend_api::MB_CUDA_PTX >= 0, "PTX backend enum is available");
    static_assert(mi::mdl::ICode_generator::TL_PTX >= 0, "MDL Core PTX backend enum is available");

    if (!check_mdl_sdk_factory()) {
        return EXIT_FAILURE;
    }
    if (!check_mdl_core_factory()) {
        return EXIT_FAILURE;
    }
    return EXIT_SUCCESS;
}
