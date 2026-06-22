#include <MaterialXRenderMsl/MslRenderer.h>

int main()
{
    MaterialX::MslRendererPtr renderer = MaterialX::MslRenderer::create(1, 1);
    return renderer ? 0 : 1;
}
