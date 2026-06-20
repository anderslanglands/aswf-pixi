#include <OpenEXR/ImfChannelList.h>
#include <OpenEXR/ImfHeader.h>

int main()
{
    OPENEXR_IMF_NAMESPACE::Header header(2, 2);
    header.channels().insert(
        "R",
        OPENEXR_IMF_NAMESPACE::Channel(OPENEXR_IMF_NAMESPACE::FLOAT));

    return header.channels().findChannel("R") == nullptr ? 1 : 0;
}
