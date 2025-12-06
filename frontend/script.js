async function uploadImage() {
    const file = document.getElementById("imageInput").files[0];
    const statusDiv = document.getElementById("status");
    const resultsDiv = document.getElementById("results");
    const jsonOutput = document.getElementById("jsonOutput");

    if (!file) {
        statusDiv.innerText = "⚠️ Please select an image first!";
        statusDiv.className = "status error";
        return;
    }

    // Show loading
    statusDiv.innerText = "🔄 Processing... (OCR → Normalize → Classify → Extract)";
    statusDiv.className = "status loading";
    resultsDiv.classList.add("hidden");

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
            statusDiv.className = "status success";
            
            jsonOutput.textContent = JSON.stringify(data, null, 2);
            resultsDiv.classList.remove("hidden");
        } else {
            throw new Error(data.error || "Processing failed");
        }
    } catch (error) {
        statusDiv.innerText = `❌ Error: ${error.message}`;
        statusDiv.className = "status error";
    }
}