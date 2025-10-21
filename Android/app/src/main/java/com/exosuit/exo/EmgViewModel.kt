package com.exosuit.exo

import android.annotation.SuppressLint
import android.app.Application
import android.bluetooth.BluetoothDevice
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.widget.Toast
import androidx.compose.runtime.State
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.ProcessLifecycleOwner
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.viewModelScope
import com.exosuit.exo.data_classes.ModelData
import com.exosuit.exo.data_classes.ModelType
import com.exosuit.exo.data_classes.RecordingStep
import com.exosuit.exo.utility.UdpMotorController
import com.google.gson.Gson
import com.ncorti.myonnaise.CommandList
import com.ncorti.myonnaise.Myo
import com.ncorti.myonnaise.MyoStatus
import com.ncorti.myonnaise.Myonnaise
import io.reactivex.Observable
import io.reactivex.android.schedulers.AndroidSchedulers
import io.reactivex.disposables.Disposable
import io.reactivex.schedulers.Schedulers
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import org.tensorflow.lite.Interpreter
import java.io.File
import java.lang.Math.abs
import java.lang.Math.sqrt
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.TimeUnit
import kotlin.math.pow


/**
 * ViewModel to handle EMG data recording, labeling, preprocessing, model training loading, and prediction.
 */

class EmgViewModel(application: Application) : AndroidViewModel(application) {

    val isRecording = mutableStateOf(false)
    val predictedValue = mutableStateOf(doubleArrayOf(0.0, 0.0, 0.0, 0.0))

    private val buffer = mutableListOf<List<Float>>()
    private var currentLabel: List<Float>? = null
    private val recordedData = mutableListOf<Pair<List<Float>, List<Float>>>()
    private var model: ModelData? = null


    // var activeModelType = ModelType.RIDGE
    var activeModelType by mutableStateOf(ModelType.NONE)

    var trainingModelType = ModelType.NONE
    private var tfliteInterpreter: Interpreter? = null

    private val _trainingStatus = MutableStateFlow("")
    val trainingStatus: StateFlow<String> = _trainingStatus


    private val _trainingProgress = MutableStateFlow(0)
    val trainingProgress: StateFlow<Int> = _trainingProgress

    private val _modelReady = MutableStateFlow(false)
    val modelReady: StateFlow<Boolean> = _modelReady


    val recordingStepsList = listOf(
        RecordingStep("Isometric Co-Contraction", listOf(1f, 0f, 0f, 0f)),
        RecordingStep("Full Extension", listOf(0f, 1f, 0f, 0f)),
        RecordingStep("Full Flexion", listOf(0f, 0f, 1f, 0f)),
        RecordingStep("Rest", listOf(0f, 0f, 0f, 1f))
    )

    private val _permissionsGranted = mutableStateOf(false)
    val permissionsGranted: State<Boolean> = _permissionsGranted

    private val _modelExists = MutableStateFlow<Boolean?>(null)
    val modelExists: StateFlow<Boolean?> = _modelExists

    private val _availableModels = MutableStateFlow<List<String>>(emptyList())
    val availableModels: StateFlow<List<String>> = _availableModels

    private val _selectedModel = MutableStateFlow<String?>(null)
    val selectedModel: StateFlow<String?> = _selectedModel

    private val _modelActive = MutableStateFlow(false)
    val modelActive: StateFlow<Boolean> = _modelActive


    private val udpController: UdpMotorController


    val motorConnectionState: StateFlow<UdpMotorController.ConnectionState>
        get() = udpController.connectionState


    init {

        udpController = UdpMotorController.getInstance(ProcessLifecycleOwner.get().lifecycleScope , getApplication())

        udpController.ridgeCallback = { modelJson ->
            try {
                // Parse the JSON to determine the model type
                val jsonObject = JSONObject(modelJson)
                val modelTypeString = jsonObject.optString("type", "RIDGE_FOR_EXO")

                // Set the appropriate training model type
                trainingModelType = when (modelTypeString) {
                    "RIDGE_FOR_EXO" -> ModelType.RIDGE_FOR_EXO
                    else -> ModelType.RIDGE_FOR_EXO
                }

                _trainingStatus.value = "${trainingModelType.name} model received, saving..."
                saveModel(modelJson)
                _trainingStatus.value = "Model saved successfully!"
                _trainingProgress.value = 100
                _modelReady.value = true
            } catch (e: Exception) {
                _trainingStatus.value = "Error parsing model: ${e.message}"
                Log.e("MyoScan", "Error parsing model JSON", e)
            }
        }

        udpController.tfliteCallback = { mlpData ->
            trainingModelType = ModelType.TFLITE
            _trainingStatus.value = "MLP/TFLite model received, saving..."
            saveModel(mlpData)
            _trainingStatus.value = "Model saved successfully!"
            _trainingProgress.value = 100
            _modelReady.value = true
        }

        udpController.progressCallback = { percent ->
            _trainingProgress.value = percent
        }

        udpController.errorCallback = { err ->
            udpController.resetModelReceived()
            _trainingStatus.value = "Server error: $err"
            Log.e("MyoScan", err)
        }

        loadModel()
    }
    var lastRecordedDataPath: String? = null

    fun sendDataToTrainingServer(csvPath: String) {
        val csvFile = File(csvPath)
        if (!csvFile.exists()) {
            _trainingStatus.value = "CSV file not found: $csvPath"
            return
        }

        val csvContent = csvFile.readText()
        _trainingProgress.value = 0
        _modelReady.value = false
        _trainingStatus.value = "Starting new training..."
        lastRecordedDataPath = csvPath
        udpController.sendTrainingData(getApplication() , csvContent, trainingModelType ) { success, message ->
            _trainingStatus.value = message
            if (success) {
                _trainingStatus.value = "Data sent, waiting for models..."
                Log.d("MyoScan", "Data sent successfully, waiting for models")
            } else {
                _trainingStatus.value = "Failed to send data: $message"
                Log.e("MyoScan", "Failed to send data: $message")
            }
        }
    }
    //Retry Training have bug in it
    fun retryTraining(csvPath: String) {
        val csvFile = File(csvPath)
        if (!csvFile.exists()) {
            _trainingStatus.value = "CSV file not found: $csvPath"
            return
        }

        // Reset training state
        _trainingProgress.value = 0
        _modelReady.value = false
        _trainingStatus.value = "Retrying training..."

        // Send data again
        val csvContent = csvFile.readText()
        udpController.sendTrainingData(getApplication() ,csvContent, trainingModelType) { success, message ->
            _trainingStatus.value = message
            if (success) {
                _trainingStatus.value = "Data sent, waiting for models..."
            } else {
                _trainingStatus.value = "Failed to send data: $message"
            }
        }
    }

    fun setPermissionsGranted(granted: Boolean) {
        _permissionsGranted.value = granted
    }

    fun setLabel(label: List<Float>) {
        currentLabel = label
    }

    fun startRecording() {
        isRecording.value = true
    }

    fun pauseRecording() {
        isRecording.value = false
    }

    fun resumeRecording() {
        isRecording.value = true
    }

    fun startSessionRecording() {
        recordedData.clear()
        currentLabel = null
    }


    fun stopRecording(onSaveComplete: (Boolean, String) -> Unit) {
        isRecording.value = false
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val header = (1..8).joinToString(",") { "ch$it" } + ",iso,extend,flex,rest"
                val csvLines =
                    recordedData.joinToString("\n") {
                        //it.first.joinToString(",") + ",${it.second}"
                        it.first.joinToString(",") + "," + it.second.joinToString(",")
                    }

                val file = File(getApplication<Application>().filesDir, "emg_raw_data.csv")
                file.writeText(header + "\n" + csvLines)

                withContext(Dispatchers.Main) {
                    onSaveComplete(true, file.absolutePath)
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    onSaveComplete(false, e.message ?: "Failed to save")
                    Log.d("MyoScan", "Error saving CSV internally: ${e.message}")
                }
            }
        }
    }


    fun onNewEmgSample(sample: List<Float>) {
        if (isRecording.value && currentLabel != null) {
            // val features = emgProcessor.processSample(sample)
            // recordedData.add(features to (currentLabel ?: 0f))
            recordedData.add(sample to (currentLabel ?: listOf(0f, 0f, 0f, 1f)))
        }
        if (!isRecording.value) {
            processSampleForPrediction(sample)
        }
    }


    private fun saveModel(data: Any) {
        try {
            val timestamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(Date())
            val modelTypeLabel = when (trainingModelType) {
                ModelType.RIDGE_FOR_EXO -> "ridge_for_exo"
                ModelType.TFLITE -> "mlp"
                else -> "unknown"
            }

            when (data) {
                is String -> {
                    val fileName = "model_${modelTypeLabel}_$timestamp.json"
                    val file = File(getApplication<Application>().filesDir, fileName)
                    file.writeText(data)

                    // Parse and load the model based on type
                    val json = JSONObject(data)
                    when (json.getString("type")) {
                        "RIDGE_FOR_EXO" -> {
                            model = Gson().fromJson(data, ModelData.RidgeExoModel::class.java)
                        }
                        // Remove other cases since we're only using RIDGE_FOR_EXO and TFLITE now
                    }

                    checkModelExists()
                    Log.d("MyoScan", "Model saved: $fileName")
                }

                is ByteArray -> {
                    // Handle TFLite model
                    val tfliteFileName = "model_mlp_$timestamp.tflite"
                    val tfliteFile = File(getApplication<Application>().filesDir, tfliteFileName)
                    tfliteFile.writeBytes(data)

                    // For MLP, create a default preprocessing model
                    model = ModelData.MLPModel(
                        preprocessing = ModelData.MLPModel.PreprocessingParams(
                            window_size = 60,
                            features = listOf("rms", "mav")
                        )
                    )

                    loadTfliteInterpreter(tfliteFileName)
                    checkModelExists()
                    Log.d("MyoScan", "TFLite model saved: $tfliteFileName")
                }
            }

        } catch (e: Exception) {
            Log.e("Training", "Failed to save model: ${e.message}")
        }
    }



    fun loadTfliteInterpreter(tflitePath: String) {
        try {
            val file = File(getApplication<Application>().filesDir, tflitePath)
            if (file.exists()) {
                tfliteInterpreter = Interpreter(file)
                _modelReady.value = true
                _selectedModel.value = file.name
                Log.d("MyoScan", "TFLite interpreter loaded from $tflitePath")

                // Set default preprocessing for MLP model
                model = ModelData.MLPModel(
                    preprocessing = ModelData.MLPModel.PreprocessingParams(
                        window_size = 60,
                        features = listOf("rms", "mav")
                    )
                )
            } else {
                Log.d("MyoScan", "TFLite file not found")
            }
        } catch (e: Exception) {
            Log.e("MyoScan", "Failed to load TFLite interpreter", e)
        }
    }

    fun checkModelExists() {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val filesDir = getApplication<Application>().filesDir
                val modelFiles = filesDir.listFiles { file ->
                    //file.name.endsWith(".json") && file.name.startsWith("model_")
                    (file.name.endsWith(".json") || file.name.endsWith(".tflite")) && file.name.startsWith(
                        "model_"
                    )
                }?.map { it.name } ?: emptyList()

                _availableModels.value = modelFiles
                _modelExists.value = modelFiles.isNotEmpty()

                Log.d("MyoScan", "Available models: ${modelFiles.joinToString()}")
            } catch (e: Exception) {
                _modelExists.value = false
                Log.d("MyoScan", "Error checking model existence: ${e.message}")
            }
        }

    }

    fun loadModel(filename: String? = null) {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val file = if (filename != null) {
                    File(getApplication<Application>().filesDir, filename)
                } else {
                    // Default to the first available model if no filename provided
                    val firstModel = _availableModels.value.firstOrNull()
                    if (firstModel != null) {
                        File(getApplication<Application>().filesDir, firstModel)
                    } else {
                        null
                    }
                }

                if (file != null && file.exists()) {
                    if (file.extension == "tflite") {
                        loadTfliteInterpreter(file.name)
                    } else {
                        val json = file.readText()
                        val jsonObj = JSONObject(json)

                        model = when (jsonObj.getString("type")) {
                            "RIDGE_FOR_EXO" -> Gson().fromJson(
                                json,
                                ModelData.RidgeExoModel::class.java
                            )

                            else -> null
                        }

                        // Log model details for debugging
                        Log.d("MyoScan", "Model loaded: ${file.name}")

                        _selectedModel.value = file.name
                        Log.d("MyoScan", "Model loaded: ${file.name}")
                    }
                } else {
                    try {
                        // Load default model if available
                        val json = getApplication<Application>().assets.open("exo_ridge_model.json")
                            .bufferedReader().use { it.readText() }
                        model = Gson().fromJson(json, ModelData.RidgeExoModel::class.java)
                        Log.d("MyoScan", "Model loaded from assets")
                    } catch (e: Exception) {
                        Log.d("MyoScan", "No model found in assets either")
                        model = null
                    }
                }
            } catch (e: Exception) {
                model = null
                Log.d("MyoScan", "Failed to load model: ${e.message}")
            }
        }
    }

    fun toggleModelActive(active: Boolean) {
        _modelActive.value = active
    }


    private val _smoothedAngle = MutableStateFlow(0f)
    val smoothedAngle: StateFlow<Float> = _smoothedAngle.asStateFlow()

    private val smoothingFactor = 0.2f

    private fun processSampleForPrediction(sample: List<Float>) {
        if (!_modelActive.value || model == null) return

        // Get window size and features based on model type
        val windowSize = when (model) {
            is ModelData.RidgeExoModel -> (model as ModelData.RidgeExoModel).preprocessing.window_size
            is ModelData.MLPModel -> (model as ModelData.MLPModel).preprocessing.window_size
            else -> 60 // Default fallback
        }

        val featuresList = when (model) {
            is ModelData.RidgeExoModel -> (model as ModelData.RidgeExoModel).preprocessing.features
            is ModelData.MLPModel -> (model as ModelData.MLPModel).preprocessing.features
            else -> listOf("rms", "mav") // Default fallback
        }

        // Update rolling buffer
        buffer.add(sample)
        if (buffer.size < windowSize) return
        if (buffer.size > windowSize) buffer.removeAt(0)

        val features = extractFeatures(buffer, featuresList)
        val prediction = predictModel(features)


        //sendPredictionValues(prediction)

        Log.d("MyoScan", "prediction : " + prediction.joinToString(", ") { "%.3f".format(it) })
        // --- Convert probabilities -> continuous angle ---

        val classAngles = listOf(0.0, -45.0, 45.0, 0.0)

        val maxIndex = prediction.indices.maxByOrNull { prediction[it] } ?: 0
        val continuousAngle = classAngles[maxIndex].toFloat()

        // --- Smooth with EMA ---
        val prevAngle = _smoothedAngle.value
        _smoothedAngle.value = prevAngle + smoothingFactor * (continuousAngle - prevAngle)

        // Log before/after smoothing
        Log.d(
            "MyoScan",
            "continuousAngle=%.3f, smoothedAngle=%.3f".format(
                continuousAngle,
                _smoothedAngle.value
            )
        )

        // Update the predicted value
        predictedValue.value = prediction
        sendPredictionValues(prediction)

    }







    //should be in this format [0.8, 0.1, 0.05, 0.05] -> Strong isometric
    fun sendPredictionValues(regressionValues: DoubleArray) {
        if (regressionValues.size != 4) {

            Log.e("UdpMotorController", "Regression values must contain exactly 4 elements")
            return
        }

        if (motorConnectionState.value != UdpMotorController.ConnectionState.CONNECTED) {
            Log.w("UdpMotorController", "Not connected, skipping regression values send")
            return
        }
        Log.d(
            "MyoScan",
            "pridiction values being sent to exo".format(
                regressionValues
            )
        )
        udpController.sendRegressionValues(regressionValues ,getApplication())
    }


    private fun predictModel(features: List<Double>): DoubleArray {
        return when (activeModelType) {
            ModelType.RIDGE_FOR_EXO -> predictRidgeExo(features)
            ModelType.TFLITE -> predictTFLite(features.map { it.toFloat() }.toFloatArray())
            else -> doubleArrayOf(0.0, 0.0, 0.0, 1.0) // Default to rest
        }
    }


    private fun predictRidgeExo(features: List<Double>): DoubleArray {
        val ridgeExoModel =
            model as? ModelData.RidgeExoModel ?: return doubleArrayOf(0.0, 0.0, 0.0, 0.0)

        val results = DoubleArray(4)
        for (i in 0 until 4) {
            val singleModel = ridgeExoModel.models[i]
            var result = singleModel.intercept
            for (j in features.indices) {
                result += features[j] * singleModel.coef[j]
            }
            // Apply softmax to ensure values sum to ~1.0
            results[i] = result
        }

        // Apply softmax here if i am not applyin in raspi rihgt?
        val expResults = results.map { kotlin.math.exp(it) }
        val sumExp = expResults.sum()
        return expResults.map { it / sumExp }.toDoubleArray()
    }


    // Track current features for UI/debug  // For Analysis
    private var _currentFeatures: List<Double>? = null

    // Store history of features + predictions for export  // For Analysis
    private val _predictionHistory = mutableListOf<Pair<List<Double>, Double>>()

    // Export buffers  // For Analysis
    private var _exportHistory: List<Pair<List<Double>, Double>> = emptyList()
    private var _exportModelInfo: String = ""


    //For Anaysis
    fun prepareForExport() {
        // Deactivate model so we don't log new samples while exporting
        _modelActive.value = false

        // Freeze the history
        _exportHistory = _predictionHistory.toList()

        // Capture model info - handle different model types
        _exportModelInfo = buildString {
            append("Model: ${_selectedModel.value ?: "Unknown"}\n")

            when (model) {
                is ModelData.RidgeExoModel -> {
                    val ridgeModel = model as ModelData.RidgeExoModel
                    append("Window size: ${ridgeModel.preprocessing.window_size}\n")
                    append("Features: ${ridgeModel.preprocessing.features.joinToString(", ")}\n")
                    append("Type: Ridge for Exo\n")
                }

                is ModelData.MLPModel -> {
                    val mlpModel = model as ModelData.MLPModel
                    append("Window size: ${mlpModel.preprocessing.window_size}\n")
                    append("Features: ${mlpModel.preprocessing.features.joinToString(", ")}\n")
                    append("Type: MLP\n")
                }

                else -> {
                    append("Window size: Unknown\n")
                    append("Features: Unknown\n")
                    append("Type: Unknown\n")
                }
            }
        }
    }

    fun exportFeaturesWithMetadata(
        filename: String, gestureDescription: String = ""
    ) {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                if (_exportHistory.isEmpty()) {
                    _trainingStatus.value = "No features captured for export."
                    return@launch
                }

                val metadata = StringBuilder()
                metadata.append(
                    "# Feature export generated on: ${
                        SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format(
                            Date()
                        )
                    }\n"
                )
                metadata.append("# $gestureDescription\n")
                metadata.append("# $_exportModelInfo\n")
                metadata.append("# \n")

                val header = StringBuilder()

                // Fixed: Specify type for emptyList
                val featureList = when (model) {
                    is ModelData.RidgeExoModel -> (model as ModelData.RidgeExoModel).preprocessing.features
                    is ModelData.MLPModel -> (model as ModelData.MLPModel).preprocessing.features
                    else -> emptyList<String>() // Explicit type
                }

                for (i in 0 until 8) {
                    for (feature in featureList) {
                        header.append("ch${i + 1}_$feature,")
                    }
                }
                header.append("iso_pred,extend_pred,flex_pred,rest_pred") // Update header for 4 outputs

                /* val dataLines = _exportHistory.joinToString("\n") { (features, preds) ->
                     features.joinToString(",") + ",${preds[0]},${preds[1]},${preds[2]},${preds[3]}"
                 }*/

                val file = File(getApplication<Application>().filesDir, filename)
                //file.writeText(metadata.toString() + header.toString() + "\n" + dataLines)

                withContext(Dispatchers.Main) {
                    _trainingStatus.value = "Features exported to $filename"
                    Toast.makeText(
                        getApplication(), "Features exported to $filename", Toast.LENGTH_SHORT
                    ).show()
                }

                Log.d("MyoScan", "Features exported with metadata: ${file.absolutePath}")
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    _trainingStatus.value = "Export failed: ${e.message}"
                }
                Log.e("MyoScan", "Error exporting features with metadata", e)
            }
        }
    }


    // Function to reactivate the model after export
    fun resumeModelAfterExport() {
        // Only reactivate if it was active before
        _modelActive.value = true
    }

    private fun extractFeatures(
        buffer: List<List<Float>>, featuresToExtract: List<String>
    ): List<Double> {
        val features = mutableListOf<Double>()

        // Extract features for each channel
        for (ch in 0 until 8) {
            val channelData = buffer.map { it[ch] }
            val rectified = channelData.map { kotlin.math.abs(it) }

            if ("rms" in featuresToExtract) {
                val rms = sqrt(rectified.sumOf { it.toDouble().pow(2) } / rectified.size)
                features.add(rms)
            }

            if ("mav" in featuresToExtract) {
                val mav = rectified.average()
                features.add(mav)
            }

            if ("var" in featuresToExtract) {
                val mean = rectified.average()
                val variance = rectified.map { (it - mean).pow(2) }.average()
                features.add(variance)
            }

            if ("wl" in featuresToExtract) {
                val wl = calculateWaveformLength(rectified.map { it.toDouble() })
                features.add(wl)
            }

            if ("zc" in featuresToExtract) {
                val zc = calculateZeroCrossings(channelData) // Use raw data for zero crossings
                features.add(zc.toDouble())
            }

            if ("ssc" in featuresToExtract) {
                val ssc =
                    calculateSlopeSignChanges(channelData) // Use raw data for slope sign changes
                features.add(ssc.toDouble())
            }
        }

        return features
    }

    private fun calculateWaveformLength(signal: List<Double>): Double {
        var sum = 0.0
        for (i in 0 until signal.size - 1) {
            sum += abs(signal[i + 1] - signal[i])
        }
        return sum
    }

    private fun calculateZeroCrossings(signal: List<Float>, threshold: Float = 0.01f): Int {
        var count = 0
        for (i in 0 until signal.size - 1) {
            val product = signal[i] * signal[i + 1]
            val difference = abs(signal[i] - signal[i + 1])

            if (product < 0 && difference >= threshold) {
                count++
            }
        }
        return count
    }

    private fun calculateSlopeSignChanges(signal: List<Float>, threshold: Float = 0.01f): Int {
        var count = 0
        for (i in 1 until signal.size - 1) {
            val diff1 = signal[i] - signal[i - 1]
            val diff2 = signal[i] - signal[i + 1]
            val product = diff1 * diff2

            if (product > threshold) {
                count++
            }
        }
        return count
    }


    private fun predictTFLite(features: FloatArray): DoubleArray {
        if (tfliteInterpreter == null) return doubleArrayOf(0.0, 0.0, 0.0, 1.0)

        val input = arrayOf(features)
        val output = Array(1) { FloatArray(4) } // 4 outputs
        tfliteInterpreter!!.run(input, output)

        // Convert to DoubleArray
        return output[0].map { it.toDouble() }.toDoubleArray()
    }


    // ---------------- BLE / Myo Functions ----------------

    private val myoManager = Myonnaise(application)
    private var myoScanDisposable: Disposable? = null

    // Holds the scanned devices
    private val _availableMyos = MutableStateFlow<List<BluetoothDevice>>(emptyList())
    val availableMyos: StateFlow<List<BluetoothDevice>> = _availableMyos

    // Holds the currently connected Myo
    private var connectedMyo: Myo? = null

    // Holds the Myo status
    private val _myoStatus = MutableStateFlow<MyoStatus>(MyoStatus.DISCONNECTED)
    val myoStatus: StateFlow<MyoStatus> = _myoStatus

    @SuppressLint("MissingPermission")
    fun scanForMyos(scanDurationMs: Long = 5000L) {
        Log.d("MyoScan", "Scan started")
        _availableMyos.value = emptyList()
        myoScanDisposable?.dispose()

        val scanObservable: Observable<BluetoothDevice> =
            myoManager.startScan().toObservable().subscribeOn(Schedulers.io())
                .observeOn(AndroidSchedulers.mainThread()).filter { device ->
                    // Only add if new
                    _availableMyos.value.none { it.address == device.address }
                }.doOnNext { device ->
                    Log.d("MyoScan", "Device found: ${device.name ?: device.address}")
                    _availableMyos.value = _availableMyos.value + device
                }

        myoScanDisposable =
            scanObservable.takeUntil(Observable.timer(scanDurationMs, TimeUnit.MILLISECONDS))
                .subscribe({},
                    { error -> Log.e("MyoScan", "Scan error", error) },
                    { Log.d("MyoScan", "Scan finished") })
    }

    private var myoStatusDisposable: Disposable? = null
    private var emgDataDisposable: Disposable? = null

    @SuppressLint("MissingPermission")
    fun connectToMyo(
        device: BluetoothDevice,
        onConnected: () -> Unit,
        onConnecting: () -> Unit,
        onError: (Throwable) -> Unit = {}
    ) {
        Log.d("MyoScan", "connectToMyo")

        if (connectedMyo?.isConnected() == true) {
            disconnectMyo()
        }

        connectedMyo = myoManager.getMyo(device)
        connectedMyo?.connect(getApplication())
        myoStatusDisposable?.dispose()

        // Notify UI that connection is starting
        onConnecting()

        myoStatusDisposable = connectedMyo?.statusObservable()?.subscribeOn(Schedulers.io())
            ?.observeOn(AndroidSchedulers.mainThread())?.subscribe({ status ->
                Log.d("MyoScan", "Status: $status")
                _myoStatus.value = status

                if (status == MyoStatus.READY) {
                    onConnected()

                    try {
                        // Start EMG streaming
                        Handler(Looper.getMainLooper()).postDelayed({
                            connectedMyo?.sendCommand(CommandList.emgUnfilteredOnly())
                            emgDataDisposable = connectedMyo?.dataFlowable()?.subscribe({ emgData ->
                                // Log.d("MyoScan", "EMG: ${emgData.joinToString()}")

                                onNewEmgSample(emgData.toList())  //  send EMG to use
                            }, { error ->
                                Log.e("MyoScan", "EMG error: ${error.message}")
                                _myoStatus.value = MyoStatus.DISCONNECTED
                                onError(error)
                            })
                        }, 500)
                    } catch (e: Exception) {

                        Log.e("MyoScan", "EMG error: ${e.message}")
                    }


                }
            }, { error ->
                // If error happens in connection flow
                Log.e("MyoScan", "Connection error: ${error.message}")
                _myoStatus.value = MyoStatus.DISCONNECTED
                onError(error)
            })
    }


    fun disconnectMyo() {
        Log.d("MyoScan", "disconnectMyo() get called")
        myoStatusDisposable?.dispose()
        connectedMyo?.disconnect()
        connectedMyo = null
        _myoStatus.value = MyoStatus.DISCONNECTED
    }

    override fun onCleared() {
        super.onCleared()
        Log.d("MyoScan", "onCleared() get called")
        try {
            myoStatusDisposable?.dispose()
            myoScanDisposable?.dispose()
            // Only cleanup session, keep persistent listener alive
            udpController.cleanupAfterSession()
            udpController.closeRegressionSocket()
            disconnectMyo()
        } catch (e: Exception) {
            Log.e("MyoScan", e.message.toString())
        }
    }

}
