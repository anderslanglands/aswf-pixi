#include <OpenEXR/openexr.h>
#include <OpenEXR/openexr_version.h>

#if OPENEXR_VERSION_MAJOR != OPENEXR_CONSUMER_EXPECT_MAJOR
#error "Unexpected OpenEXR major version header"
#endif

#if OPENEXR_VERSION_MINOR != OPENEXR_CONSUMER_EXPECT_MINOR
#error "Unexpected OpenEXR minor version header"
#endif

#if OPENEXR_VERSION_PATCH != OPENEXR_CONSUMER_EXPECT_PATCH
#error "Unexpected OpenEXR patch version header"
#endif

int main(void)
{
    int major = 0;
    int minor = 0;
    int patch = 0;
    const char* extra = 0;

    exr_get_library_version(&major, &minor, &patch, &extra);

    return (
        major == OPENEXR_CONSUMER_EXPECT_MAJOR &&
        minor == OPENEXR_CONSUMER_EXPECT_MINOR &&
        patch == OPENEXR_CONSUMER_EXPECT_PATCH) ? 0 : 1;
}
