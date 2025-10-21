package com.exosuit.exo.data_classes

// Sealed class for different model types

sealed class ModelData {
    data class MLPModel(
        val preprocessing: PreprocessingParams
    ) : ModelData() {
        data class PreprocessingParams(
            val window_size: Int,
            val features: List<String>
        )
    }

    data class RidgeExoModel(
        val models: List<SingleRidgeModel>,
        val preprocessing: PreprocessingParams
    ) : ModelData() {
        data class SingleRidgeModel(
            val intercept: Double,
            val coef: List<Double>
        )

        data class PreprocessingParams(
            val window_size: Int,
            val features: List<String>,
            val mse: Double? = null,
            val mae: Double? = null
        )
    }
}