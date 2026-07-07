#include <MaterialXGenOsl/OslShaderGenerator.h>
#include <MaterialXRenderOsl/OslRenderer.h>

int main()
{
    MaterialX::OslRendererPtr renderer = MaterialX::OslRenderer::create(1, 1);
    MaterialX::ShaderGeneratorPtr generator = MaterialX::OslShaderGenerator::create();
    return renderer && generator &&
        generator->getTarget() == MaterialX::OslShaderGenerator::TARGET ? 0 : 1;
}
