#include <opensubdiv/osd/mtlComputeEvaluator.h>

int opensubdiv_metal_header_check()
{
    OpenSubdiv::Osd::MTLComputeEvaluator* evaluator = nullptr;
    return evaluator == nullptr ? 0 : 1;
}
