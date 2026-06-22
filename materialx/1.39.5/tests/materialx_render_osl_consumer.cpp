#include <MaterialXRenderOsl/OslRenderer.h>

int main()
{
    MaterialX::OslRendererPtr renderer = MaterialX::OslRenderer::create(1, 1);
    return renderer ? 0 : 1;
}
