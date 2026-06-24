#include <MaterialXRenderSlang/SlangRenderer.h>
#include <MaterialXRenderSlang/TextureBaker.h>

namespace
{
using TextureBakerFactory = MaterialX::TextureBakerSlangPtr (*)(unsigned int, unsigned int, MaterialX::Image::BaseType);
TextureBakerFactory volatile createTextureBaker = &MaterialX::TextureBakerSlang::create;
}

int main()
{
    MaterialX::SlangRendererPtr renderer = MaterialX::SlangRenderer::create(1, 1);
    return (renderer && createTextureBaker != nullptr) ? 0 : 1;
}
