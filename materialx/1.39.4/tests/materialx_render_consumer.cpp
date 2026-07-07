#include <MaterialXRender/Image.h>
#include <MaterialXRenderGlsl/GlslRenderer.h>

int main()
{
    MaterialX::ImagePtr image = MaterialX::Image::create(1, 1, 3, MaterialX::Image::BaseType::UINT8);
    MaterialX::GlslRendererPtr renderer = MaterialX::GlslRenderer::create(1, 1);
    return image && renderer ? 0 : 1;
}
