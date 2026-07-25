import { FiClock, FiDownload, FiList } from "react-icons/fi";
import { downloadUrl } from "../api";

function formatDuration(seconds) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function VideoResult({ video, onQueue }) {
  if (!video) return null;

  const sourceUrl = video.format_id.startsWith("http")
    ? video.format_id
    : `https://www.tiktok.com/@x/video/${video.id}`;
  const dlUrl = downloadUrl(sourceUrl, video.format_id);

  return (
    <div className="video-result fade-in">
      <div className="video-thumb-wrap">
        <img
          className="video-thumb"
          src={video.thumbnail || ""}
          alt={video.caption ? `Thumbnail for ${video.caption}` : "Video thumbnail"}
          loading="lazy"
        />
        {video.duration > 0 && (
          <span className="duration-badge">
            <FiClock size={12} aria-hidden="true" /> {formatDuration(video.duration)}
          </span>
        )}
      </div>

      <div className="video-info">
        {video.author && <span className="video-author">{video.author}</span>}
        <p className="video-caption">{video.caption || "No description"}</p>
      </div>

      <div className="video-actions">
        <a href={dlUrl} className="btn btn-primary" title="Download this video">
          <FiDownload size={16} aria-hidden="true" /> Download
        </a>
        <button
          className="btn btn-secondary"
          onClick={() => onQueue(video.format_id)}
          title="Add to queue"
        >
          <FiList size={16} aria-hidden="true" /> Queue
        </button>
      </div>
    </div>
  );
}