module.exports = async (_req, res) => {
  return res.status(200).json({
    mentee_count: 0,
    mentor_count: 0,
    ready_to_match: false,
    note: "Vercel serverless mode does not persist local JSON storage.",
  });
};
