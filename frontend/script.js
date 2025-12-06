async function uploadImage() {
    const file = document.getElementById("imageInput").files[0];
    if (!file) {
        alert("Select an image first!");
        return;
    }

    const formData = new FormData();
    formData.append("image", file);

    const res = await fetch("http://localhost:3000/upload", {
        method: "POST",
        body: formData
    });

    const data = await res.json();
    document.getElementById("status").innerText = "Upload complete! Check backend console.";
}
