#include <ultrahdr_api.h>

#include <cstring>
#include <iostream>

int main()
{
    if (UHDR_LIB_VERSION != 10400 || std::strcmp(UHDR_LIB_VERSION_STR, "1.4.0") != 0)
    {
        std::cerr << "Unexpected libuhdr version: " << UHDR_LIB_VERSION_STR << '\n';
        return 1;
    }

    uhdr_codec_private_t* encoder = uhdr_create_encoder();
    if (!encoder)
    {
        std::cerr << "Failed to create encoder\n";
        return 1;
    }

    uhdr_error_info_t status = uhdr_enc_set_quality(encoder, 90, UHDR_BASE_IMG);
    if (status.error_code != UHDR_CODEC_OK)
    {
        std::cerr << "Failed to set encoder quality: " << status.detail << '\n';
        uhdr_release_encoder(encoder);
        return 1;
    }
    uhdr_release_encoder(encoder);

    uhdr_codec_private_t* decoder = uhdr_create_decoder();
    if (!decoder)
    {
        std::cerr << "Failed to create decoder\n";
        return 1;
    }

    status = uhdr_dec_set_out_img_format(decoder, UHDR_IMG_FMT_32bppRGBA8888);
    if (status.error_code != UHDR_CODEC_OK)
    {
        std::cerr << "Failed to set decoder format: " << status.detail << '\n';
        uhdr_release_decoder(decoder);
        return 1;
    }
    uhdr_release_decoder(decoder);

    return 0;
}
