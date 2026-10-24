#include <opensubdiv/osd/cpuVertexBuffer.h>
#include <opensubdiv/version.h>

#if defined(OPENSUBDIV_CONSUMER_REQUIRE_CUDA)
#include <opensubdiv/osd/cudaEvaluator.h>
#include <opensubdiv/osd/cudaVertexBuffer.h>
#endif

#if defined(OPENSUBDIV_CONSUMER_REQUIRE_OPENGL)
#include <opensubdiv/osd/glComputeEvaluator.h>
#include <opensubdiv/osd/glVertexBuffer.h>
#endif

#include <array>

int main()
{
    static_assert(OPENSUBDIV_VERSION_NUMBER == 30700, "unexpected OpenSubdiv version");

#if defined(OPENSUBDIV_CONSUMER_REQUIRE_CUDA)
    OpenSubdiv::Osd::CudaVertexBuffer* cudaVertices = nullptr;
    OpenSubdiv::Osd::CudaEvaluator const* cudaEvaluator = nullptr;
    (void)cudaVertices;
    (void)cudaEvaluator;
#endif

#if defined(OPENSUBDIV_CONSUMER_REQUIRE_OPENGL)
    OpenSubdiv::Osd::GLVertexBuffer* glVertices = nullptr;
    OpenSubdiv::Osd::GLComputeEvaluator const* glEvaluator = nullptr;
    OpenSubdiv::Osd::GLComputeEvaluator::ID glBufferId = 0;
    (void)glVertices;
    (void)glEvaluator;
    (void)glBufferId;
#endif

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
