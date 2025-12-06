import express from "express";
import multer from "multer";
import cors from "cors";
import { spawn } from "child_process";
import path from "path";

const app = express();
app.use(cors());
app.use(express.json());

// Store uploaded images in /uploads
const upload = multer({ dest: "uploads/" });

app.post("/upload", upload.single("image"), (req, res) => {
    const imagePath = req.file.path;

    console.log("Image received:", imagePath);

    // Call python script
    const python = spawn("python", ["extract_table.py", imagePath]);

    python.stdout.on("data", data => {
        console.log(data.toString());
    });

    python.stderr.on("data", data => {
        console.error("Python error:", data.toString());
    });

    python.on("close", () => {
        res.json({ status: "done" });
    });
});

app.listen(3000, () => console.log("Server running on port 3000"));
