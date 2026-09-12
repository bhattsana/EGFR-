import { motion } from "framer-motion";
import { Link } from "react-router-dom";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-black text-white relative overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(0,255,170,0.15),transparent)]"></div>

      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen px-6">
        <motion.h1
          initial={{opacity:0,y:40}}
          animate={{opacity:1,y:0}}
          transition={{duration:1}}
          className="text-7xl font-black text-center"
        >
          EGFR AI SCREENING
        </motion.h1>

        <p className="mt-8 text-xl text-gray-400 max-w-2xl text-center">
          AI-powered molecular intelligence platform for accelerated NSCLC drug discovery.
        </p>

        <Link
          to="/analyzer"
          className="mt-10 px-8 py-4 bg-emerald-500 rounded-2xl font-bold text-xl hover:bg-emerald-400 transition"
        >
          Launch Platform
        </Link>
      </div>
    </div>
  );
}