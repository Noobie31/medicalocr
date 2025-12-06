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

    // Step 1: Call extract_table.py
    const pythonExtract = spawn("python", ["extract_table.py", imagePath]);
    
    let extractedData = "";

    pythonExtract.stdout.on("data", data => {
        const output = data.toString();
        extractedData += output;
        console.log("Table extraction output:");
        console.log(output);
    });

    pythonExtract.stderr.on("data", data => {
        console.error("Python extraction error:", data.toString());
    });

    pythonExtract.on("close", (code) => {
        if (code !== 0) {
            console.error("Extract table script failed");
            return res.status(500).json({ status: "error", message: "Table extraction failed" });
        }

        console.log("\n--- Starting LLM API Request ---\n");

        // Step 2: Call lmmapireq.py and pipe the extracted data to it
        const pythonLLM = spawn("python", ["lmmapireq.py"]);
        
        // Send the extracted table data to lmmapireq.py via stdin
        pythonLLM.stdin.write(extractedData);
        pythonLLM.stdin.end();

        pythonLLM.stdout.on("data", data => {
            console.log(data.toString());
        });

        pythonLLM.stderr.on("data", data => {
            console.error("LLM API error:", data.toString());
        });

        pythonLLM.on("close", (llmCode) => {
            if (llmCode !== 0) {
                console.error("LLM API request failed");
                return res.status(500).json({ status: "error", message: "LLM processing failed" });
            }
            
            console.log("\n--- Pipeline Complete ---\n");
            res.json({ status: "done", message: "Table extracted and analyzed by AI" });
        });
    });
});

app.listen(3000, () => console.log("Server running on port 3000"));