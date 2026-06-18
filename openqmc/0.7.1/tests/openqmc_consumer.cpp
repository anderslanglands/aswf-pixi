#include <oqmc/oqmc.h>

#include <array>
#include <cstddef>

template <std::size_t Size>
struct CacheStorage
{
    alignas(std::max_align_t) std::array<char, Size == 0 ? 1 : Size> bytes{};

    void* data()
    {
        return Size == 0 ? nullptr : bytes.data();
    }
};

template <typename Sampler>
bool sample_in_unit_square()
{
    CacheStorage<Sampler::cacheSize> cache{};
    Sampler::initialiseCache(cache.data());

    const auto domain = Sampler(1, 2, 0, 3, cache.data());

    float sample[2] = {};
    domain.template drawSample<2>(sample);

    return sample[0] >= 0.0f && sample[0] < 1.0f && sample[1] >= 0.0f &&
           sample[1] < 1.0f;
}

int main()
{
    return sample_in_unit_square<oqmc::PmjBnSampler>() &&
                   sample_in_unit_square<oqmc::SobolBnSampler>() &&
                   sample_in_unit_square<oqmc::LatticeBnSampler>()
               ? 0
               : 1;
}
