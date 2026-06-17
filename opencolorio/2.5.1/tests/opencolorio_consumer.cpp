#include <OpenColorIO/OpenColorIO.h>

#include <cmath>
#include <cstring>
#include <iostream>

namespace OCIO = OCIO_NAMESPACE;

int main()
{
    const char * version = OCIO::GetVersion();
    if (!version || std::strcmp(version, "2.5.1") != 0)
    {
        std::cerr << "Unexpected OpenColorIO version: " << (version ? version : "<null>") << '\n';
        return 1;
    }

    if (OCIO::GetVersionHex() == 0)
    {
        std::cerr << "Unexpected zero OpenColorIO version hex\n";
        return 1;
    }

    OCIO::MatrixTransformRcPtr transform = OCIO::MatrixTransform::Create();
    const double offset[4] = { 0.1, 0.0, 0.0, 0.0 };
    transform->setOffset(offset);

    OCIO::ConstConfigRcPtr config = OCIO::Config::CreateRaw();
    OCIO::ConstProcessorRcPtr processor = config->getProcessor(transform);
    OCIO::ConstCPUProcessorRcPtr cpu = processor->getDefaultCPUProcessor();

    float pixel[4] = { 0.2f, 0.3f, 0.4f, 1.0f };
    cpu->applyRGBA(pixel);

    if (std::fabs(pixel[0] - 0.3f) > 1e-6f ||
        std::fabs(pixel[1] - 0.3f) > 1e-6f ||
        std::fabs(pixel[2] - 0.4f) > 1e-6f ||
        std::fabs(pixel[3] - 1.0f) > 1e-6f)
    {
        std::cerr << "Unexpected processor result: "
                  << pixel[0] << ", "
                  << pixel[1] << ", "
                  << pixel[2] << ", "
                  << pixel[3] << '\n';
        return 1;
    }

    return 0;
}
