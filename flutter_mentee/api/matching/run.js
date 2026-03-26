module.exports = async (_req, res) => {
  return res.status(501).json({
    detail:
      "Matching endpoint is not enabled in Vercel serverless mode. Deploy the FastAPI backend for matching.",
  });
};
