#include <OpenImageIO/imageio.h>
#include <OpenImageIO/oiioversion.h>
#include <OpenImageIO/strutil.h>

#include <string>

int main()
{
    if (std::string(OIIO_VERSION_STRING) != OPENIMAGEIO_EXPECTED_VERSION) {
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
