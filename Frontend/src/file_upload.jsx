import React, { useRef } from "react";
import axios from "axios";

const FileUpload = ({ selectedFile, setSelectedFile, onUpload }) => {
  const fileInputRef = useRef();

  const onFileChange = async (e) => {
    const file = e.target.files[0];
    setSelectedFile(file);
    
    // Auto-upload when file is selected
    if (file) {
      await onFileUpload(file);
    }
  };

  const onFileUpload = async (file) => {
    if (!file) {
      alert("Please select a file first");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post("http://127.0.0.1:8000/uploadfile", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });
      
      // Call the callback with the response
      if (onUpload) {
        onUpload(response.data);
      }
      
      setSelectedFile(null);
    } catch (err) {
      console.error(err);
      alert("Error uploading file: " + (err.response?.data?.error || err.message));
      setSelectedFile(null);
    }
  };

  return (
    <div>
      {/* Hidden input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={onFileChange}
        className="hidden"
        accept=".pdf"
      />

      {/* Upload icon trigger */}
      <div
        onClick={() => fileInputRef.current.click()}
        className="p-2 bg-[#1c1c1c] hover:bg-[#242424] text-[#cfcfcf] rounded-full cursor-pointer transition-colors"
        title="Upload PDF file"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={1.5}
          stroke="currentColor"
          className="w-5 h-5"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.233-2.33A3 3 0 0116.5 19.5H6.75z"
          />
        </svg>
      </div>
    </div>
  );
};

export default FileUpload;