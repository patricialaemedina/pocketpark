const qrcoded = window.qrcode;

const video = document.createElement("video");
const canvasElement = document.getElementById("qr-canvas");
const canvas = canvasElement.getContext("2d");

const qrResult = document.getElementById("qr-result");
const outputData = document.getElementById("outputData");
const btnScanQR = document.getElementById("btn-scan-qr");

let scanning = false;

qrcoded.callback = res => {
  if (res) {
    outputData.innerText = res;
    scanning = false;

    video.srcObject.getTracks().forEach(track => {
      track.stop();
    });

    qrResult.hidden = false;
    canvasElement.hidden = true;
    btnScanQR.hidden = false;

    sendDataToDjango(res);
  }
};

function sendDataToDjango(data) {
  const xhr = new XMLHttpRequest();
  
  const url = 'process_qr';
  
  xhr.open('POST', url, true);
  xhr.setRequestHeader('Content-Type', 'application/json;charset=UTF-8');
  
  const jsonData = JSON.stringify({ data: data });
  
  xhr.onload = function () {
    if (xhr.status === 200) {

      const response = JSON.parse(xhr.responseText);
      
      validData.innerText = response.message;

      const additionalData = document.getElementById('additional-data');

      if (response.message === 'VALID') {
        additionalData.hidden = false;
        validData.style.color = 'green';
        
        const userElement = document.getElementById("user");
        const slotElement = document.getElementById("slot");
        const startTimeElement = document.getElementById("start_time");
        const licensePlateElement = document.getElementById("license_plate");
        const vehicleModelElement = document.getElementById("vehicle_model");
        const vehicleMakeElement = document.getElementById("vehicle_make");
        const vehicleColorElement = document.getElementById("vehicle_color");

        const startDateTime = new Date(response.start_time);
        const formattedStartTime = startDateTime.toLocaleString();

        userElement.innerText = response.user;
        slotElement.innerText = response.slot;
        startTimeElement.innerText = formattedStartTime;
        licensePlateElement.innerText = response.license_plate;
        vehicleModelElement.innerText = response.vehicle_model;
        vehicleMakeElement.innerText = response.vehicle_make;
        vehicleColorElement.innerText = response.vehicle_color;
      }

      else {  
        validData.style.color = 'red';
        additionalData.hidden = true;
      }

    } else {
      console.error('Error:', xhr.statusText);
    }
  };
  
  // Send the request with the data
  xhr.send(jsonData);
}

btnScanQR.onclick = () => {
  navigator.mediaDevices
    .getUserMedia({ video: { facingMode: "environment" } })
    .then(function(stream) {
      scanning = true;
      qrResult.hidden = true;
      btnScanQR.hidden = true;
      canvasElement.hidden = false;
      video.setAttribute("playsinline", true); // required to tell iOS safari we don't want fullscreen
      video.srcObject = stream;
      video.play();
      tick();
      scan();
    });
};

function tick() {
  canvasElement.height = video.videoHeight;
  canvasElement.width = video.videoWidth;
  canvas.drawImage(video, 0, 0, canvasElement.width, canvasElement.height);

  scanning && requestAnimationFrame(tick);
}

function scan() {
  try {
    qrcoded.decode();
  } catch (e) {
    setTimeout(scan, 300);
  }
}