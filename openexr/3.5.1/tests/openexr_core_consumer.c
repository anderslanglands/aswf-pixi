#include <OpenEXR/openexr.h>

int main(void)
{
    int major = 0;
    int minor = 0;
    int patch = 0;
    const char* extra = 0;

    exr_get_library_version(&major, &minor, &patch, &extra);

    return (major == 3 && minor == 4 && patch == 12) ? 0 : 1;
}
