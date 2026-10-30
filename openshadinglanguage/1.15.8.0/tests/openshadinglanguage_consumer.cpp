#include <OSL/oslexec.h>
#include <OSL/oslquery.h>
#include <OSL/oslversion.h>

int main()
{
    OSL::OSLQuery query;
    if (query.nparams() != 0) {
        return 1;
    }
    if (OSL_VERSION_MAJOR != 1 || OSL_VERSION_MINOR != 15) {
        return 2;
    }

    using RegisterJITGlobal = void (*)(const char*, void*);
    volatile RegisterJITGlobal register_jit_global = &OSL::register_JIT_Global;
    if (register_jit_global == nullptr) {
        return 3;
    }
    return 0;
}
