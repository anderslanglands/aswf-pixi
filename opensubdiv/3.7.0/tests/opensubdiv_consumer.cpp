#include <opensubdiv/osd/cpuVertexBuffer.h>
#include <opensubdiv/version.h>

#include <array>

int main()
{
    static_assert(OPENSUBDIV_VERSION_NUMBER == 30700, "unexpected OpenSubdiv version");

    using OpenSubdiv::Osd::CpuVertexBuffer;

    CpuVertexBuffer* vertices = CpuVertexBuffer::Create(3, 2);
    if (vertices == nullptr) {
        return 1;
    }

    std::array<float, 6> values = {{0.0f, 1.0f, 2.0f, 3.0f, 4.0f, 5.0f}};
    vertices->UpdateData(values.data(), 0, 2);

    if (vertices->GetNumElements() != 3 || vertices->GetNumVertices() != 2) {
        delete vertices;
        return 2;
    }

    float* data = vertices->BindCpuBuffer();
    if (data == nullptr || data[4] != 4.0f) {
        delete vertices;
        return 3;
    }

    delete vertices;
    return 0;
}
