#include <OpenImageIO/imageio.h>
#include <OpenImageIO/oiioversion.h>
#include <OpenImageIO/strutil.h>

#include <string>

int main()
{
    static_assert(OIIO_VERSION_MAJOR == 3, "unexpected OIIO major version");
    static_assert(OIIO_VERSION_MINOR == 1, "unexpected OIIO minor version");
    static_assert(OIIO_VERSION_PATCH == 14, "unexpected OIIO patch version");
    static_assert(OIIO_VERSION_TWEAK == 0, "unexpected OIIO tweak version");

    if (std::string(OIIO_VERSION_STRING) != "3.1.14.0") {
        return 1;
    }
    if (!OIIO::Strutil::contains("OpenImageIO", "Image")) {
        return 2;
    }

    OIIO::ImageSpec spec(2, 2, 3, OIIO::TypeDesc::UINT8);
    if (spec.width != 2 || spec.height != 2 || spec.nchannels != 3) {
        return 3;
    }

    return 0;
}
