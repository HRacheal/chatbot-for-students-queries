import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { FaUserGraduate } from "react-icons/fa";
import GradientText from "./ui/GradientText";
import { api } from "../lib/api";

function UserLogin() {
  const [credentials, setCredentials] = useState({
    username: "",
    password: "",
  });
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const handleSubmit =async (e) => {
    e.preventDefault();
    setError(null);
    // console.log(credentials)
    if (!credentials.username || !credentials.password) {
      setError("Please fill in all fields");
      return;
    }
    // console.log(credentials)
    try {
      const response = await api.post("/api/login", {
        username: credentials.username,
        password: credentials.password,
      });
      
      if (response.data.token) {
        localStorage.setItem("userToken", response.data.token);
        navigate("/");
      }
    } catch (err) {
      console.log(err);
      setError("Invalid credentials");
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center px-4">
      <div className="max-w-md w-full space-y-8">
        <div className="flex flex-col items-center">
          <FaUserGraduate className="text-8xl text-indigo-500" />
          <GradientText className="mt-6 text-center text-3xl font-extrabold">
            User Login
          </GradientText>
        </div>
        
        <form onSubmit={handleSubmit} className="space-y-6 mt-8">
          {error && (
            <div className="text-red-500 text-center text-sm">{error}</div>
          )}
          <div className="rounded-md shadow-sm -space-y-px">
            <div>
              <input
                type="text"
                placeholder="Username"
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-700 placeholder-gray-500 text-white bg-gray-800 rounded-t-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                value={credentials.username}
                onChange={(e) =>
                  setCredentials({ ...credentials, username: e.target.value })
                }
              />
            </div>
            <div>
              <input
                type="password"
                placeholder="Password"
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-700 placeholder-gray-500 text-white bg-gray-800 rounded-b-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                value={credentials.password}
                onChange={(e) =>
                  setCredentials({ ...credentials, password: e.target.value })
                }
              />
            </div>
          </div>
          <div>
            <button
              type="submit"
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors duration-200"
            >
              Sign in
            </button>
          <button
            type="button"
            onClick={() => navigate("/")}
            className="mt-2 w-full flex justify-center py-2 px-4 border border-indigo-600 text-indigo-600 rounded-md hover:bg-indigo-700 hover:text-white transition-colors duration-200"
          >
            Go Back
          </button>
          </div>
          <div className="text-center text-sm">
            <span className="text-gray-500">Don't have an account? </span>
            <Link to="/signup" className="text-indigo-500 hover:text-indigo-400">
              Sign up
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}

export default UserLogin;
