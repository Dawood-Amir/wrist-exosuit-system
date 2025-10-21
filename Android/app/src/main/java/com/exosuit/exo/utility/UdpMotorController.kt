package com.exosuit.exo.utility

import android.content.Context
import android.net.wifi.WifiManager
import android.util.Base64
import android.util.Log
import com.exosuit.exo.data_classes.ModelType
import com.exosuit.exo.data_classes.MotorSettings
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import org.json.JSONObject
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.net.SocketTimeoutException
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.concurrent.locks.ReentrantLock


class UdpMotorController private constructor(private val appScope: CoroutineScope) {

    companion object { // just pull the current wifi's ip.
        @Volatile
        private var instance: UdpMotorController? = null

       //private const val serverIp = "192.168.1.16"
        private var serverIp: String? = null
        private const val motorPort = 3350  // Changed to match Python motor_settings_port
        private const val startSignalPort = 3352  // Changed to match Python start_signal_port
        private const val disconnectPort = 3358
        //private const val trainingServerIp = "192.168.1.16"
        private var trainingServerIp: String? =  null
        private const val trainingServerPort = 12346
        private const val trainedModelListenPort = 12347


        fun getRaspiServerIp(context: Context): String { //Change if needed
            return "10.207.176.1"
        }
        fun getTrainingServerIp(context: Context): String {
            return "10.207.176.1"
        }

            fun getInstance(appScope: CoroutineScope , context: Context): UdpMotorController {
            return instance ?: synchronized(this) {
                instance ?: UdpMotorController(appScope).also {
                    instance = it

                    serverIp = getLocalIp(context) // remove if dont need later
                    trainingServerIp = getLocalIp(context)

                }
            }
        }
/*        fun getInstance(appScope: CoroutineScope): UdpMotorController {
            return instance ?: synchronized(this) {
                instance ?: UdpMotorController(appScope).also {
                    instance = it

                }

            }
        }*/


        fun getLocalIp(context: Context): String {
            val wm = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
            val ipInt = wm.connectionInfo.ipAddress
            val ipString = String.format(
                "%d.%d.%d.%d",
                ipInt and 0xFF,
                ipInt shr 8 and 0xFF,
                ipInt shr 16 and 0xFF,
                ipInt shr 24 and 0xFF
            )

            // Log the IP
            Log.d("WristEMG", "Local IP: $ipString")

            return ipString
        }
    }

    // --- UDP Sockets ---
    private var sendSocket: DatagramSocket? = null
    private var receiveModelSocket: DatagramSocket? = null

    // --- Model listener ---
    private var modelListenerJob: Job? = null

    // --- Motor connection state ---
    private val _connectionState = MutableStateFlow(ConnectionState.DISCONNECTED)
    val connectionState: StateFlow<ConnectionState> = _connectionState.asStateFlow()


    //Motor Connection

    private var confirmationSocket: DatagramSocket? = null
    private var confirmationListenerJob: Job? = null

    private var regressionSocket: DatagramSocket? = null
    private val regressionSocketLock = ReentrantLock() // Use ReentrantLock instead of Mutex


    // --- MLP chunk storage ---
    private val mlpChunks = mutableMapOf<Int, ByteArray>()
    @Volatile
    private var modelReceived = false

    // --- Callbacks ---
    var ridgeCallback: ((String) -> Unit)? = null
    var tfliteCallback: ((ByteArray) -> Unit)? = null
    var progressCallback: ((Int) -> Unit)? = null
    var errorCallback: ((String) -> Unit)? = null

    init {
        ensureReceiveSocket()
        startPersistentListener()
        startConfirmationListener()
    }




    /*******************Motor Control******************/
    // --- Public API ---
    private fun startConfirmationListener() {
        confirmationListenerJob = appScope.launch(Dispatchers.IO) {
            val socket = DatagramSocket(3351) // Listen on confirmation port
            socket.soTimeout = 5000 // 5 second timeout

            while (isActive) {
                val buffer = ByteArray(1024)
                val packet = DatagramPacket(buffer, buffer.size)
                try {
                    socket.receive(packet)
                    val message = String(packet.data, 0, packet.length)
                    if (message.contains("success") && _connectionState.value == ConnectionState.SETTINGS_SENT) {
                        _connectionState.value = ConnectionState.READY_TO_START
                        Log.d("UdpMotorController", "Settings confirmed, ready to start")
                    }
                } catch (e: SocketTimeoutException) {
                    // Continue listening
                } catch (e: Exception) {
                    Log.e("UdpMotorController", "Confirmation listener error: ${e.message}")
                }
            }
        }
    }
    fun sendDisconnectSignal(context: Context, onComplete: (Boolean, String?) -> Unit) {
        appScope.launch(Dispatchers.IO) {
            try {
                val socket = DatagramSocket()
                val message = JSONObject().apply {
                    put("command", "disconnect")
                }.toString()
                val packet = DatagramPacket(
                    message.toByteArray(),
                    message.length,
                    InetAddress.getByName(getRaspiServerIp(context)),
                    disconnectPort
                )
                socket.send(packet)
                socket.close()

                // Update connection state to DISCONNECTED
                _connectionState.value = ConnectionState.DISCONNECTED
                onComplete(true, null)
            } catch (e: Exception) {
                onComplete(false, e.message)
            }
        }
    }
    fun sendMotorSettings(context: Context ,settings: MotorSettings, onComplete: (Boolean, String?) -> Unit  ) {
        appScope.launch(Dispatchers.IO) {
            try {
                val socket = DatagramSocket()
                val message = settings.toJson()
                val packet = DatagramPacket(
                    message.toByteArray(),
                    message.length,
                    InetAddress.getByName(getRaspiServerIp(context)),
                    motorPort
                )
                socket.send(packet)
                socket.close()

                _connectionState.value = ConnectionState.SETTINGS_SENT
                onComplete(true, null)
            } catch (e: Exception) {
                _connectionState.value = ConnectionState.ERROR
                onComplete(false, e.message)
            }
        }
    }

    fun sendStartSignal( context: Context , onComplete: (Boolean, String?) -> Unit ) {
        if (_connectionState.value != ConnectionState.READY_TO_START) {
            onComplete(false, "Not ready to start")
            return
        }

        appScope.launch(Dispatchers.IO) {
            try {
                val socket = DatagramSocket()
                val message = JSONObject().apply {
                    put("command", "start")
                }.toString()
                val packet = DatagramPacket(
                    message.toByteArray(),
                    message.length,
                    InetAddress.getByName(getRaspiServerIp(context)),
                    startSignalPort
                )
                socket.send(packet)
                socket.close()

                _connectionState.value = ConnectionState.CONNECTED
                onComplete(true, null)
            } catch (e: Exception) {
                _connectionState.value = ConnectionState.ERROR
                onComplete(false, e.message)
            }
        }
    }


    fun sendRegressionValues(regressionValues: DoubleArray ,context: Context) {
        if (regressionValues.size != 4) {
            Log.e("UdpMotorController", "Regression values must contain exactly 4 elements")
            return
        }

        if (connectionState.value != ConnectionState.CONNECTED) {
            Log.w("UdpMotorController", "Not connected, skipping regression values send")
            return
        }

        appScope.launch(Dispatchers.IO) {
            try {
                // Get or create socket with thread safety using ReentrantLock
                val socket = regressionSocketLock.withLock {
                    if (regressionSocket == null || regressionSocket!!.isClosed) {
                        regressionSocket?.close() // Close if exists but is closed
                        regressionSocket = DatagramSocket().apply {
                            reuseAddress = true
                            soTimeout = 100 // Set a reasonable timeout
                        }
                    }
                    regressionSocket!!
                }

                val byteBuffer = ByteBuffer.allocate(32)
                byteBuffer.order(ByteOrder.LITTLE_ENDIAN)

                regressionValues.forEach { value ->
                    byteBuffer.putDouble(value)
                }

                val packet = DatagramPacket(
                    byteBuffer.array(),
                    byteBuffer.array().size,
                    InetAddress.getByName(getRaspiServerIp(context )),
                    3340 // myo_reg_val_port from Python config
                )

                socket.send(packet)
            } catch (e: Exception) {
                Log.e("UdpMotorController", "Failed to send regression values: ${e.message}")
                // Close socket on error to ensure it's recreated next time
                closeRegressionSocket()
            }
        }
    }

    // Add this extension function for ReentrantLock
    private inline fun <T> ReentrantLock.withLock(action: () -> T): T {
        lock()
        try {
            return action()
        } finally {
            unlock()
        }
    }

    // Add this method to clean up the socket when no longer needed
    fun closeRegressionSocket() {
        regressionSocketLock.withLock {
            regressionSocket?.close()
            regressionSocket = null
        }
    }


        /*

            fun sendRegressionValues(regressionValues: DoubleArray) {
                if (regressionValues.size != 4) {
                    Log.e("UdpMotorController", "Regression values must contain exactly 4 elements")
                    return
                }

                if (connectionState.value != ConnectionState.CONNECTED) {
                    Log.w("UdpMotorController", "Not connected, skipping regression values send")
                    return
                }

                appScope.launch(Dispatchers.IO) {
                    try {
                        val socket = DatagramSocket()
                        val byteBuffer = ByteBuffer.allocate(32)
                        byteBuffer.order(ByteOrder.LITTLE_ENDIAN)

                        regressionValues.forEach { value ->
                            byteBuffer.putDouble(value)
                        }

                        val packet = DatagramPacket(
                            byteBuffer.array(),
                            byteBuffer.array().size,
                            InetAddress.getByName(serverIp),
                            3340 // myo_reg_val_port from Python config
                        )
                        socket.send(packet)
                        socket.close()
                    } catch (e: Exception) {
                        Log.e("UdpMotorController", "Failed to send regression values: ${e.message}")
                    }
                }
            }

        */

    /*******************Motor Control******************/


    private fun ensureReceiveSocket() {
        if (receiveModelSocket == null || receiveModelSocket!!.isClosed) {
            receiveModelSocket = DatagramSocket(trainedModelListenPort)
            receiveModelSocket!!.soTimeout = 2000
        }
    }

    private fun startPersistentListener() {
        if (modelListenerJob?.isActive == true) return

        modelListenerJob = appScope.launch(Dispatchers.IO) {
            val socket = receiveModelSocket ?: return@launch
            val buffer = ByteArray(65507)

            while (isActive) {
                val packet = DatagramPacket(buffer, buffer.size)
                try {
                    socket.receive(packet)
                    val msg = String(packet.data, 0, packet.length)
                    Log.d("MyoScan", "Received UDP message: $msg")
                    when {
                        msg.startsWith("{") -> { // Ridge model
                            markModelReceived()
                            ridgeCallback?.invoke(msg)
                        }
                        msg.startsWith("MLP_TFLITE_CHUNK:") -> handleMLPChunk(msg) { fullModel ->
                            markModelReceived()
                            tfliteCallback?.invoke(fullModel)
                        }
                        msg.startsWith("TRAINING_PROGRESS") -> {
                            Log.d("MyoScan" ,"TRAINING_PROGRESS match")

                            val progressPattern = """TRAINING_PROGRESS[:\s]*(\d+)/(\d+)""".toRegex()
                            val match = progressPattern.find(msg)
                            if (match != null) {
                                val (currentStr, totalStr) = match.destructured
                                val current = currentStr.toIntOrNull() ?: 0
                                val total = totalStr.toIntOrNull() ?: 1
                                val percent = (current.toFloat() / total.toFloat() * 100).toInt()
                                Log.d("MyoScan", "Parsed progress: $current/$total = $percent%")
                                progressCallback?.invoke(percent)
                            }else{
                                Log.d("MyoScan" ,"TRAINING_PROGRESS match = null")
                            }
                        }
                        msg.startsWith("SERVER_ERROR:") -> errorCallback?.invoke(msg.removePrefix("SERVER_ERROR:"))
                    }

                } catch (_: SocketTimeoutException) {
                    // continue listening
                } catch (e: Exception) {
                    Log.e("MyoScan", "Listener exception: ${e.message}", e)
                }
            }
        }
    }

    private fun handleMLPChunk(msg: String, onComplete: (ByteArray) -> Unit) {
        try {
            val parts = msg.split(":", limit = 4)
            val chunkIndex = parts[1].toInt()
            val totalChunks = parts[2].toInt()
            val chunkBytes = Base64.decode(parts[3], Base64.DEFAULT)
            mlpChunks[chunkIndex] = chunkBytes

            if (mlpChunks.size == totalChunks) {
                val fullModel = ByteArray(mlpChunks.values.sumOf { it.size })
                var offset = 0
                for (i in 0 until totalChunks) {
                    val chunk = mlpChunks[i]!!
                    System.arraycopy(chunk, 0, fullModel, offset, chunk.size)
                    offset += chunk.size
                }
                mlpChunks.clear()
                onComplete(fullModel)
            }
        } catch (e: Exception) {
            Log.e("MyoScan", "MLP chunk processing failed: ${e.message}", e)
        }
    }

    fun prepareForNewTraining() {
        mlpChunks.clear()
        resetModelReceived()
        sendSocket?.close()
        sendSocket = null
    }

    fun sendTrainingData(context: Context ,csvData: String, modelType: ModelType, onComplete: (Boolean, String) -> Unit ) {
        prepareForNewTraining()
        sendSocket = DatagramSocket().apply { reuseAddress = true }

        appScope.launch(Dispatchers.IO) {
            try {
                val socket = sendSocket ?: return@launch
                val data = csvData.toByteArray()
                val trainingAddress = InetAddress.getByName(getTrainingServerIp(context))
                val chunkSize = 1400
                val totalChunks = (data.size + chunkSize - 1) / chunkSize
                val chunksMap = (0 until totalChunks).associateWith { i ->
                    val start = i * chunkSize
                    val end = minOf(start + chunkSize, data.size)
                    data.copyOfRange(start, end)
                }

                // Send header
                val header = "MODEL_TYPE:${modelType.name}\nTOTAL_CHUNKS:$totalChunks"
                var headerAck = false
                repeat(3) {
                    if (!headerAck) {
                        socket.send(DatagramPacket(header.toByteArray(), header.length, trainingAddress, trainingServerPort))
                        try {
                            val ackBuf = ByteArray(32)
                            val ackPacket = DatagramPacket(ackBuf, ackBuf.size)
                            socket.soTimeout = 2000
                            socket.receive(ackPacket)
                            if (String(ackPacket.data, 0, ackPacket.length) == "HEADER_ACK") headerAck = true
                        } catch (_: SocketTimeoutException) {}
                    }
                }

                if (!headerAck) {
                    onComplete(false, "Header ACK not received")
                    return@launch
                }

                // Send chunks
                for ((i, chunk) in chunksMap) {
                    var ack = false
                    var retries = 0
                    while (!ack && retries < 5) {
                        val headerBytes = ByteBuffer.allocate(8).putInt(i).putInt(totalChunks).array()
                        val packetData = headerBytes + chunk
                        socket.send(DatagramPacket(packetData, packetData.size, trainingAddress, trainingServerPort))

                        try {
                            val buf = ByteArray(32)
                            val recv = DatagramPacket(buf, buf.size)
                            socket.soTimeout = 1000
                            socket.receive(recv)
                            val msg = String(recv.data, 0, recv.length)
                            if (msg == "ACK:$i") ack = true
                        } catch (_: SocketTimeoutException) { retries++ }
                    }

                    if (!ack) {
                        onComplete(false, "Chunk $i failed")
                        return@launch
                    }
                }

                // Wait for model to arrive
                val start = System.currentTimeMillis()
                while (!isModelReceived() && System.currentTimeMillis() - start < 20000) delay(100)

                socket.close()
                sendSocket = null

                if (isModelReceived()) onComplete(true, "Model received")
                else onComplete(false, "Model not received in time")

            } catch (e: Exception) {
                onComplete(false, e.message ?: "Unknown error")
            }
        }
    }

    fun markModelReceived() { modelReceived = true }
    fun resetModelReceived() { modelReceived = false }
    fun isModelReceived(): Boolean = modelReceived

    /** Called after a training session to clear temporary data but keep listener alive */
    fun cleanupAfterSession() {
        mlpChunks.clear()
        sendSocket?.close()
        sendSocket = null
        resetModelReceived()
    }

    /** Full shutdown (optional, only on app exit) */
    fun shutdownController() {
        try {
            modelListenerJob?.cancel()
            modelListenerJob = null
            mlpChunks.clear()
            sendSocket?.close()
            sendSocket = null
            receiveModelSocket?.close()
            receiveModelSocket = null
            confirmationListenerJob?.cancel()
            confirmationSocket?.close()
            closeRegressionSocket()
        }catch (e:Exception){Log.e("MyoScan",e.message.toString())}

    }
    enum class ConnectionState {
        DISCONNECTED,      // No connection to motor
        SETTINGS_SENT,     // Motor settings sent but not confirmed
        READY_TO_START,    // Settings confirmed, ready to start
        CONNECTED,         // System started and running
        ERROR
    }
}

