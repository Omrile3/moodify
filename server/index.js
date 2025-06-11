const express = require('express');
const cors = require('cors');
const fs = require('fs');
const csv = require('csv-parser');

const app = express();
const PORT = process.env.PORT || 5000;

app.use(cors());
app.use(express.json());

const csvFilePath = './server/music_data.csv'; // Place your CSV file in the 'server' directory

app.get('/api/songs', (req, res) => {
  const results = [];
  fs.createReadStream(csvFilePath)
    .pipe(csv())
    .on('data', (data) => results.push(data))
    .on('end', () => {
      res.json(results);
    })
    .on('error', (err) => {
      console.error('Error reading CSV file:', err);
      res.status(500).json({ error: 'Failed to read CSV file' });
    });
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
