#include <MaterialXRenderSlang/SlangRenderer.h>

int main()
{
    MaterialX::SlangRendererPtr renderer = MaterialX::SlangRenderer::create(1, 1);
    return renderer ? 0 : 1;
}
