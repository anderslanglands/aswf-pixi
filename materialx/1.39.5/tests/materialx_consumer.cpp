#include <MaterialXCore/Document.h>
#include <MaterialXCore/Util.h>
#include <MaterialXFormat/XmlIo.h>
#include <MaterialXGenGlsl/GlslShaderGenerator.h>
#include <MaterialXGenMdl/MdlShaderGenerator.h>
#include <MaterialXGenMsl/MslShaderGenerator.h>
#include <MaterialXGenOsl/OslShaderGenerator.h>
#include <MaterialXGenSlang/SlangShaderGenerator.h>

#include <iostream>

int main()
{
    MaterialX::DocumentPtr doc = MaterialX::Document::createDocument<MaterialX::Document>();
    MaterialX::ShaderGeneratorPtr glsl = MaterialX::GlslShaderGenerator::create();
    MaterialX::ShaderGeneratorPtr mdl = MaterialX::MdlShaderGenerator::create();
    MaterialX::ShaderGeneratorPtr msl = MaterialX::MslShaderGenerator::create();
    MaterialX::ShaderGeneratorPtr osl = MaterialX::OslShaderGenerator::create();
    MaterialX::ShaderGeneratorPtr slang = MaterialX::SlangShaderGenerator::create();
    const std::string xml = MaterialX::writeToXmlString(doc);

    if (!doc || !glsl || !mdl || !msl || !osl || !slang || xml.empty() ||
        glsl->getTarget() != MaterialX::GlslShaderGenerator::TARGET ||
        mdl->getTarget() != MaterialX::MdlShaderGenerator::TARGET ||
        msl->getTarget() != MaterialX::MslShaderGenerator::TARGET ||
        osl->getTarget() != MaterialX::OslShaderGenerator::TARGET ||
        slang->getTarget() != MaterialX::SlangShaderGenerator::TARGET ||
        MaterialX::getVersionString().empty())
    {
        return 1;
    }

    std::cout << MaterialX::getVersionString() << '\n';
}
