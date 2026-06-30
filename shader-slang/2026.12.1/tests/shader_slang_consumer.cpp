#include <slang.h>

#include <stdexcept>

int main()
{
    slang::IGlobalSession* globalSession = nullptr;
    const SlangResult result = slang_createGlobalSession(SLANG_API_VERSION, &globalSession);
    if (SLANG_FAILED(result) || globalSession == nullptr) {
        throw std::runtime_error("failed to create Slang global session");
    }

    if (globalSession->findProfile("glsl_450") == SLANG_PROFILE_UNKNOWN) {
        globalSession->release();
        throw std::runtime_error("Slang did not report glsl_450 profile support");
    }

    globalSession->release();
    slang_shutdown();
    return 0;
}
