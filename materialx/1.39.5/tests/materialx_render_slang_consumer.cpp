#include <MaterialXRenderSlang/SlangRenderer.h>
#include <MaterialXRenderSlang/TextureBaker.h>

int main()
{
    MaterialX::SlangRendererPtr renderer = MaterialX::SlangRenderer::create(1, 1);
    MaterialX::TextureBakerSlangPtr baker = MaterialX::TextureBakerSlang::create(1, 1);
    return renderer && baker ? 0 : 1;
}
