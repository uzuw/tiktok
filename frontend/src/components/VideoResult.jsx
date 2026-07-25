import { FiDownload, FiClock, FiList } from "react-icons/fi";
import { downloadUrl } from "../api";

function formatDuration(s) {
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

export default function VideoResult({ video, onQueue }) {
  if (!video) return null;

  const dlUrl = downloadUrl(video.format_id.startsWith("http") ? video.format_id : `https://www.tiktok.com/@x/video/${video.id}`, video.format_id);

  return (
    <div className="video-result fade-in">
      <div className="video-thumb-wrap">
        <img className="video-thumb" src={video.thumbnail || ""} alt={video.caption || "Video thumbnail"} loading="lazy" />
        {video.duration > 0 && (
          <span className="duration-badge">
            <FiClock size={12} /> {formatDuration(video.duration)}
          </span>
        )}
      </div>
      <div className="video-info">
        {video.author && <span className="video-author">{video.author}</span>}
        <p className="video-caption">{video.caption || "No description"}</p>
      </div>
      <div className="video-actions">
        <a href={dlUrl} className="btn btn-primary" title="Download">
          <FiDownload size={16} /> Download
        </a>
        <button className="btn btn-secondary" onClick={() => onQueue(video.format_id)} title="Add to queue">
          <FiList size={16} /> Queue
        </button>
      </div>
    </div>
  );
}
