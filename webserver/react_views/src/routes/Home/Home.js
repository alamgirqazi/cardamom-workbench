import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { ListGroup } from "react-bootstrap";
import { NavBar } from "../../components";
import axios from "axios";

import {
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  ListItemIcon,
  CircularProgress,
  Typography,
  Box,
} from "@mui/material";
import {
  Folder as FolderIcon,
  UploadFile as UploadFileIcon,
} from "@mui/icons-material";
import { InsertDriveFile as InsertDriveFileIcon } from "@mui/icons-material";

import "./Home.css";

const Home = ({
  user,
  setUser,
  documents,
  setDocuments,
  setFileInfo,
  setUserId,
}) => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(true);
  const r = () => {
    const userId = user.id;
    const get_files_url = process.env.REACT_APP_PORT
      ? `http://${process.env.REACT_APP_HOST}:${process.env.REACT_APP_PORT}/api/get_files?user=` +
        userId
      : `https://${process.env.REACT_APP_HOST}/api/get_files?user=` + userId;
    axios
      .get(get_files_url)
      .then(function (response) {
        const documents = response.data.file_contents;
        setDocuments(documents);
        setUser({ ...user, documents: documents });
        console.log("somehow this gets called");
        localStorage.setItem("user", JSON.stringify(user));
        setIsLoading(false);
      })
      .catch(function (err) {
        console.log(err);
      });
  };

  useEffect(() => {
    /*if(user.documents){
		setIsLoading(false);
		setDocuments(user.documents)
		return
	}*/
    r();
  }, []);
  /*useEffect(() => {
    // Update the document title using the browser API
    if (userId === undefined && localStorage.getItem('userId') === null) {
      navigate("/login", { replace: true });
    }
    else if(userId === undefined && localStorage.getItem('userId') !== null){
      setUserId(localStorage.getItem('userId'));
    }
    r();

  }, [userId]);*/

  // return (
  //   <div>
  //     <NavBar
  //       setUser={setUser}
  //       pages={[
  //         { path: "/", name: "Home" },
  //         { path: "/fileupload", name: "File Upload" },
  //       ]}
  //     />
  //     <h1> Welcome {user.name} </h1>
  //     {isLoading ? (
  //       <div>Loading...</div>
  //     ) : documents.length > 0 ? (
  //       documents.map((doc) => {
  //         return (
  //           <ListGroup key={doc.filename} className="list-item">
  //             <ListGroup.Item
  //               action
  //               onClick={() => {
  //                 setFileInfo({
  //                   ...doc,
  //                 });
  //                 navigate(`/tokeniser/${doc.file_id}`);
  //               }}
  //             >
  //               {doc.filename}
  //             </ListGroup.Item>
  //           </ListGroup>
  //         );
  //       })
  //     ) : (
  //       <div>No Documents Uploaded!</div>
  //     )}
  //   </div>
  // );
  return (
    <div>
      <NavBar
        setUser={setUser}
        user={user}
        pages={[
          { path: "/", name: "Home" },
          { path: "/fileupload", name: "File Upload" },
        ]}
      />
      <div>
        <Typography variant="h4" gutterBottom>
          Welcome {user.name}
        </Typography>
        <Box
          display="flex"
          justifyContent="center"
          alignItems="center"
          minHeight="50vh"
        >
          {isLoading ? (
            <CircularProgress />
          ) : documents.length > 0 ? (
            <List>
              {documents.map((doc) => (
                <ListItem key={doc.filename} disablePadding>
                  <ListItemButton
                    onClick={() => {
                      setFileInfo({
                        ...doc,
                      });
                      navigate(`/tokeniser/${doc.file_id}`);
                    }}
                  >
                    <ListItemIcon>
                      <InsertDriveFileIcon style={{ color: "blue" }} />
                    </ListItemIcon>
                    <ListItemText
                      primary={doc.filename}
                      primaryTypographyProps={{ color: "primary" }}
                    />
                  </ListItemButton>
                </ListItem>
              ))}
            </List>
          ) : (
            <Typography variant="h6" color="textSecondary">
              No Documents Uploaded!
            </Typography>
          )}
        </Box>
      </div>
    </div>
  );
};

export default Home;
