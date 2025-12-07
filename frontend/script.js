async function uploadImage() {
    const file = document.getElementById("imageInput").files[0];
    const statusDiv = document.getElementById("status");
    const resultsDiv = document.getElementById("results");
    const jsonOutput = document.getElementById("jsonOutput");

    if (!file) {
        alert("⚠️ Please select an image first!");
        return;
    }

    // Show loading
    statusDiv.innerText = "🔄 Processing... (OCR → Normalize → Classify → Extract)";
    statusDiv.style.display = "block";
    statusDiv.style.padding = "15px";
    statusDiv.style.background = "#fff3cd";
    statusDiv.style.color = "#856404";
    statusDiv.style.borderRadius = "6px";
    statusDiv.style.marginBottom = "20px";
    
    if (resultsDiv) resultsDiv.style.display = "none";

    const formData = new FormData();
    formData.append("image", file);

    try {
        const res = await fetch("http://localhost:3000/upload", {
            method: "POST",
            body: formData
        });

        const data = await res.json();

        if (data.status === "ok" || data.status === "no_amounts_found") {
            statusDiv.innerText = data.status === "ok" 
                ? "✅ Extraction complete!" 
                : "⚠️ No amounts found in document";
            statusDiv.style.background = "#d4edda";
            statusDiv.style.color = "#155724";
            
            if (jsonOutput) {
                jsonOutput.textContent = JSON.stringify(data, null, 2);
            }
            if (resultsDiv) {
                resultsDiv.style.display = "block";
            }
        } else {
            throw new Error(data.error || "Processing failed");
        }
    } catch (error) {
        statusDiv.innerText = `❌ Error: ${error.message}`;
        statusDiv.style.background = "#f8d7da";
        statusDiv.style.color = "#721c24";
    }
}