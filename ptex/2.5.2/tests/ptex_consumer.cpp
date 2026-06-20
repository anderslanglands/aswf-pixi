#include <Ptexture.h>

#include <array>
#include <cstring>
#include <iostream>

int main()
{
    if (PtexLibraryMajorVersion != 2 || PtexLibraryMinorVersion != 5)
    {
        std::cerr << "Unexpected Ptex library version: " << PtexLibraryMajorVersion << '.'
                  << PtexLibraryMinorVersion << '\n';
        return 1;
    }

    const char* path = "ptex_consumer.ptx";
    Ptex::String error;
    PtexWriter* writer = PtexWriter::open(
        path, Ptex::mt_quad, Ptex::dt_uint8, 3, -1, 1, error, false);
    if (!writer)
    {
        std::cerr << "Failed to open Ptex writer: " << error.c_str() << '\n';
        return 1;
    }

    writer->setBorderModes(Ptex::m_clamp, Ptex::m_clamp);
    writer->setEdgeFilterMode(Ptex::efm_none);
    writer->writeMeta("producer", "aswf-pixi");

    const Ptex::FaceInfo face_info(Ptex::Res(1, 1));
    const std::array<unsigned char, 12> pixels = {
        0, 32, 64,
        96, 128, 160,
        192, 224, 255,
        16, 48, 80,
    };
    if (!writer->writeFace(0, face_info, pixels.data()))
    {
        std::cerr << "Failed to write Ptex face\n";
        writer->release();
        return 1;
    }

    if (!writer->close(error))
    {
        std::cerr << "Failed to close Ptex writer: " << error.c_str() << '\n';
        writer->release();
        return 1;
    }
    writer->release();

    PtexPtr<PtexTexture> texture(PtexTexture::open(path, error));
    if (!texture)
    {
        std::cerr << "Failed to open Ptex texture: " << error.c_str() << '\n';
        return 1;
    }

    const PtexTexture::Info info = texture->getInfo();
    if (info.meshType != Ptex::mt_quad || info.dataType != Ptex::dt_uint8 ||
        info.numChannels != 3 || info.alphaChannel != -1 || info.numFaces != 1)
    {
        std::cerr << "Unexpected Ptex texture metadata\n";
        return 1;
    }

    const Ptex::FaceInfo& read_face = texture->getFaceInfo(0);
    if (read_face.res != face_info.res || read_face.isConstant())
    {
        std::cerr << "Unexpected Ptex face metadata\n";
        return 1;
    }

    std::array<unsigned char, 12> read_pixels = {};
    texture->getData(0, read_pixels.data(), 0);
    if (read_pixels != pixels)
    {
        std::cerr << "Unexpected Ptex texel readback\n";
        return 1;
    }

    std::array<float, 3> pixel = {};
    texture->getPixel(0, 1, 0, pixel.data(), 0, 3);
    if (pixel[0] <= 0.36f || pixel[0] >= 0.38f ||
        pixel[1] <= 0.50f || pixel[1] >= 0.51f ||
        pixel[2] <= 0.62f || pixel[2] >= 0.63f)
    {
        std::cerr << "Unexpected Ptex normalized pixel readback\n";
        return 1;
    }

    PtexPtr<PtexMetaData> meta(texture->getMetaData());
    const char* producer = nullptr;
    meta->getValue("producer", producer);
    if (!producer || std::strcmp(producer, "aswf-pixi") != 0)
    {
        std::cerr << "Unexpected Ptex metadata readback\n";
        return 1;
    }

    return 0;
}
