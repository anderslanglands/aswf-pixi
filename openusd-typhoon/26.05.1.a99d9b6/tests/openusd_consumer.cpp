#include <pxr/pxr.h>
#include <pxr/usd/usd/stage.h>

int main()
{
    PXR_NAMESPACE_USING_DIRECTIVE

    auto stage = UsdStage::CreateInMemory();
    return stage ? 0 : 1;
}
