#include <MaterialXCore/Document.h>
#include <MaterialXCore/Util.h>
#include <MaterialXFormat/XmlIo.h>
#include <MaterialXGenGlsl/GlslShaderGenerator.h>
#include <MaterialXGenMsl/MslShaderGenerator.h>

#include <iostream>

int main()
{
    MaterialX::DocumentPtr doc = MaterialX::Document::createDocument<MaterialX::Document>();
    MaterialX::ShaderGeneratorPtr glsl = MaterialX::GlslShaderGenerator::create();
    MaterialX::ShaderGeneratorPtr msl = MaterialX::MslShaderGenerator::create();
    const std::string xml = MaterialX::writeToXmlString(doc);

    if (!doc || !glsl || !msl || xml.empty() ||
        glsl->getTarget() != MaterialX::GlslShaderGenerator::TARGET ||
        msl->getTarget() != MaterialX::MslShaderGenerator::TARGET ||
        MaterialX::getVersionString().empty())
    {
        return 1;
    }

    std::cout << MaterialX::getVersionString() << '\n';
}
